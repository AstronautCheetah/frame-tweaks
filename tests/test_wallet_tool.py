"""wallet-tool (packs/core/wallet): terminal tools from Homebrew behind the shared KDE wallet. It
offers the commands of the formulae you installed (brew leaves) and of casks, not those of
dependencies, Homebrew itself, gh (the Wallet install's own wrapper) or the formulae Frame
Tweaks' tweaks install and run; protecting writes a
wrapper in ~/.local/bin that runs the real command through with-keyring; --list and --remove
follow; a program of yours there is never overwritten or removed. A fake Homebrew prefix stands
in for /home/linuxbrew/.linuxbrew.

claude's wrapper also runs it through wallet-token, which hands it a token kept in the wallet
(CLAUDE_CODE_OAUTH_TOKEN): Claude Code keeps its sign-in in a plain-text file whatever the
keyring. --store-token puts one there (never echoed), --remove and --forget-token take it out;
wallet-token itself against a stand-in Secret Service."""
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script, sandbox_env, stub  # noqa: E402

TOOL = ROOT / "packs/core/wallet/wallet-tool"
TOKEN = ROOT / "packs/core/wallet/wallet-token"


class WalletTool(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        t = Path(tmp.name)
        self.home, prefix = t / "home", t / "linuxbrew"
        self.prefix = prefix
        for owner, cmd in (("Caskroom/claude-code@latest/2.1", "claude"), ("Cellar/ripgrep/14.1/bin", "rg"),
                           ("Cellar/pcre2/10.4/bin", "pcre2grep"), ("Cellar/gh/2.80/bin", "gh"),
                           ("Cellar/whisper.cpp/1.8/bin", "whisper-cli")):
            stub(prefix / owner, cmd, f'echo "real {cmd} $*"')
            (prefix / "bin").mkdir(parents=True, exist_ok=True)
            (prefix / "bin" / cmd).symlink_to(prefix / owner / cmd)
        stub(prefix / "bin", "brew", 'case "$1" in leaves) printf "ripgrep\\ngh\\nwhisper.cpp\\n" ;; esac')
        # (what Frame Tweaks' tweaks install, as the Wallet install writes it: whisper-cpp for Dictation)
        (t / "brew-for-tweaks").write_text("tesseract\nwhisper-cpp\nwl-clipboard\n")
        # (with-keyring: just runs the command, saying it did)
        stub(self.home / ".local/bin", "with-keyring", 'echo "with-keyring"; exec "$@"')
        # (wallet-token: says it ran, keeps what it's given to store in a file, counts forgets)
        stub(self.home / ".local/bin", "wallet-token",
             'case "$1" in run) echo "wallet-token run $2"; shift 2; exec "$@" ;;'
             ' store) cat > "$HOME/stored-$2" ;; forget) echo forget >> "$HOME/forgot-$2" ;; esac')
        self.env = sandbox_env(self.home, FRAME_TWEAKS_BREW=prefix / "bin/brew",
                               FRAME_TWEAKS_BREW_FOR_TWEAKS=t / "brew-for-tweaks")

    def tool(self, *args, ok=True, input=""):
        r = subprocess.run([sys.executable, str(TOOL), *args], env=self.env, capture_output=True, text=True, timeout=30,
                           input=input)
        if ok is not None:
            self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def listed(self, arg):
        return dict(line.split("\t", 1) for line in self.tool(arg).stdout.splitlines())

    def test_offers_what_you_installed_not_dependencies_brew_gh_or_what_tweaks_run(self):
        # (whisper.cpp is a leaf, but Dictation runs whisper-cli: it mustn't wait for the wallet)
        self.assertEqual(self.listed("--candidates"), {"claude": "claude-code@latest", "rg": "ripgrep"})

    def test_protect_runs_it_through_with_keyring_then_remove(self):
        self.tool("claude")
        wrapper = self.home / ".local/bin/claude"
        self.assertTrue(os.access(wrapper, os.X_OK))
        r = subprocess.run([str(wrapper), "doctor"], env=self.env, capture_output=True, text=True, timeout=30)
        # (claude through wallet-token too, which hands it the wallet's token)
        self.assertEqual(r.stdout.split("\n")[:3], ["with-keyring", "wallet-token run claude", "real claude doctor"])
        self.assertEqual(self.listed("--list"), {"claude": str(self.prefix / "bin/claude")})
        self.assertNotIn("claude", self.listed("--candidates"))
        self.tool("--remove", "claude")
        self.assertFalse(wrapper.exists())
        self.assertIn("claude", self.listed("--candidates"))

    def test_a_program_of_yours_is_left_alone(self):
        mine = stub(self.home / ".local/bin", "rg", "echo mine")
        r = self.tool("rg", ok=False)
        self.assertIn("a program of yours", r.stderr)
        r = self.tool("--remove", "rg", ok=False)
        self.assertIn("not protected by wallet-tool", r.stderr)
        self.assertEqual(mine.read_text(), "#!/bin/bash\necho mine\n")

    def test_gh_and_unknown_commands_are_refused(self):
        self.assertIn("Wallet tweak's install", self.tool("gh", ok=False).stderr)
        self.assertIn("not in Homebrew", self.tool("nosuch", ok=False).stderr)
        self.assertIn("not a command name", self.tool("../evil", ok=False).stderr)

    def test_only_claude_goes_through_wallet_token(self):
        self.tool("rg")
        self.assertNotIn("wallet-token", (self.home / ".local/bin/rg").read_text())
        self.assertEqual(self.listed("--list"), {"rg": str(self.prefix / "bin/rg")})
        self.assertIn("no token to keep", self.tool("--store-token", "rg", ok=False).stderr)

    def test_the_commands_with_tokens_are_the_same_in_both_programs(self):
        self.assertEqual(set(load_script(TOOL).TOKENS), set(load_script(TOKEN).ENV))

    def test_store_token_protects_and_stores_from_stdin_never_echoing_it(self):
        # (A wrapper from before tokens: storing one writes it again, now handing the token over.)
        old = stub(self.home / ".local/bin", "claude", f'# wallet-tool: claude\nexec "$HOME/.local/bin/with-keyring" '
                   f'{self.prefix}/bin/claude "$@"')
        cred = self.home / ".claude/.credentials.json"
        cred.parent.mkdir()
        cred.write_text(json.dumps({"claudeAiOauth": {"accessToken": "sk-old-secret"}, "mcpOAuth": {"x": "mcp-secret"}}))
        r = self.tool("--store-token", "claude", input=f"  {SECRET}  \n")
        self.assertEqual((self.home / "stored-claude").read_text(), SECRET + "\n")
        self.assertIn("wallet-token\" run claude", old.read_text())
        out = r.stdout + r.stderr
        for secret in (SECRET, "sk-old-secret", "mcp-secret"):
            self.assertNotIn(secret, out)
        # (not a terminal: no question, so the plain-text file stays, and it says how to remove it)
        self.assertIn("also holds: mcpOAuth", out)
        self.assertIn(f"rm {cred}", out)
        self.assertTrue(cred.exists())

    def test_store_token_with_nothing_stores_nothing(self):
        self.assertIn("Nothing stored", self.tool("--store-token", "claude", input="\n", ok=False).stderr)
        self.assertFalse((self.home / "stored-claude").exists())

    def test_remove_forgets_the_token_only_while_the_wallet_is_unlocked(self):
        unlock = stub(self.home / ".local/bin", "wallet-unlock", "echo locked")
        self.tool("claude")
        r = self.tool("--remove", "claude")
        self.assertIn("wallet-tool --forget-token claude removes it", r.stdout)    # (no password dialog for a Remove)
        self.assertFalse((self.home / "forgot-claude").exists())
        unlock.write_text("#!/bin/bash\necho unlocked\n")
        self.tool("claude")
        self.tool("--remove", "claude")
        self.assertEqual((self.home / "forgot-claude").read_text(), "forget\n")
        self.tool("--forget-token", "claude")       # (asks for the password if it must)
        self.assertEqual((self.home / "forgot-claude").read_text(), "forget\nforget\n")


SECRET = "sk-ant-oat01-" + "Ab3_-" * 12     # (a made-up token)


class FakeSecretService:
    """The wallet's Secret Service as wallet-token reaches it through jeepney: items found by
    their attributes, a "plain" session, CreateItem replacing an item with the same attributes.
    Locked, it hands out no secrets and asks for a prompt to change anything."""
    def __init__(self):
        self.items, self.locked, self.opened, self.n = {}, False, 0, 0

    def send_and_get_reply(self, msg):
        addr, method, signature, body = msg
        reply = lambda *b: types.SimpleNamespace(header=types.SimpleNamespace(message_type="return"), body=b)
        assert addr.bus_name == "org.freedesktop.secrets"
        if method == "OpenSession":
            assert body == ("plain", ("s", ""))
            return reply(("s", ""), "/session/1")
        if method == "SearchItems":
            found = [p for p, (attrs, _s) in self.items.items() if attrs == body[0]]
            return reply([] if self.locked else found, found if self.locked else [])
        if method == "GetSecrets":
            items, session = body
            assert session == "/session/1"
            return reply({} if self.locked else {p: (session, b"", self.items[p][1], "text/plain") for p in items})
        if method == "CreateItem":
            assert addr.object_path == "/org/freedesktop/secrets/collection/kdewallet"
            props, (session, _params, value, _type), replace = body
            if self.locked:
                return reply("/", "/prompt/1")
            attrs = props["org.freedesktop.Secret.Item.Attributes"][1]
            path = next((p for p, (a, _s) in self.items.items() if a == attrs and replace), None)
            if path is None:
                self.n += 1
                path = f"/item/{self.n}"
            self.items[path] = (attrs, bytes(value))
            return reply(path, "/")
        if method == "Delete":
            if self.locked:
                return reply("/prompt/2")
            del self.items[addr.object_path]
            return reply("/")
        raise AssertionError(f"D-Bus {method}: not expected")

    def close(self):
        pass

    def jeepney(self):
        j = types.ModuleType("jeepney")
        j.DBusAddress = lambda object_path, bus_name=None, interface=None: types.SimpleNamespace(
            object_path=object_path, bus_name=bus_name, interface=interface)
        j.MessageType = types.SimpleNamespace(error="error", method_return="return")
        j.new_method_call = lambda addr, method, signature=None, body=(): (addr, method, signature, body)
        blocking = types.ModuleType("jeepney.io.blocking")

        def connect(bus):
            assert bus.startswith("unix:path=/run/user/")      # (the outer bus: where the wallet is)
            self.opened += 1
            return self
        blocking.open_dbus_connection = connect
        return {"jeepney": j, "jeepney.io": types.ModuleType("jeepney.io"), "jeepney.io.blocking": blocking}


class WalletToken(unittest.TestCase):
    """wallet-token: the token into the wallet and out of it again, and claude run with it in its
    environment only; never in its output."""
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.wt = load_script(TOKEN)
        self.wt.HINTED = Path(tmp.name) / "state"
        self.wallet = FakeSecretService()
        p = mock.patch.dict(sys.modules, self.wallet.jeepney())
        p.start()
        self.addCleanup(p.stop)

    def main(self, *args, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with mock.patch.object(sys, "stdin", io.StringIO(stdin)), redirect_stdout(out), redirect_stderr(err):
            try:
                self.wt.main(list(args))
            except SystemExit as e:
                code = e.code
        self.assertNotIn(SECRET, out.getvalue() + err.getvalue() + str(code))
        return code, out.getvalue(), err.getvalue()

    def run_claude(self, environ=None):
        """wallet-token run claude: what it would exec (path, argv, environment), and what it said."""
        ran = []

        def execve(path, argv, env):
            ran.append((path, argv, env))
            raise SystemExit(0)
        with mock.patch.object(self.wt.os, "execve", execve), mock.patch.dict(os.environ, environ or {}, clear=False):
            if not environ:
                os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
            _code, _out, err = self.main("run", "claude", "/brew/bin/claude", "--continue")
        self.assertEqual(ran[0][:2], ("/brew/bin/claude", ["/brew/bin/claude", "--continue"]))
        return ran[0][2], err

    def test_stored_token_reaches_claude_in_its_environment(self):
        code, out, _err = self.main("store", "claude", stdin=SECRET + "\n")
        self.assertEqual((code, out), (0, "claude: token stored in the wallet.\n"))
        self.assertEqual([s for _a, s in self.wallet.items.values()], [SECRET.encode()])
        env, err = self.run_claude()
        self.assertEqual(env["CLAUDE_CODE_OAUTH_TOKEN"], SECRET)
        self.assertEqual(err, "")
        self.assertEqual(self.main("status", "claude")[:2], (0, "stored\n"))
        # (a new token replaces the old one: one item)
        self.main("store", "claude", stdin=SECRET[::-1] + "\n")
        self.assertEqual(len(self.wallet.items), 1)

    def test_without_a_token_claude_runs_as_it_is_and_hears_once_how_to_store_one(self):
        env, err = self.run_claude()
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", env)
        self.assertIn("wallet-tool --store-token claude", err)
        self.assertEqual(self.run_claude()[1], "")
        self.main("store", "claude", stdin=SECRET + "\n")
        self.main("forget", "claude")
        self.assertIn("wallet-tool --store-token claude", self.run_claude()[1])     # (forgotten: said again)

    def test_a_token_you_set_yourself_stands(self):
        self.main("store", "claude", stdin=SECRET + "\n")
        self.wallet.opened = 0
        env, _err = self.run_claude({"CLAUDE_CODE_OAUTH_TOKEN": "mine"})
        self.assertEqual(env["CLAUDE_CODE_OAUTH_TOKEN"], "mine")
        self.assertEqual(self.wallet.opened, 0)

    def test_claude_still_runs_when_the_wallet_cant_be_read(self):
        self.main("store", "claude", stdin=SECRET + "\n")
        self.wallet.locked = True
        env, err = self.run_claude()
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", env)
        self.assertIn("couldn't read the wallet (the wallet is locked)", err)
        with mock.patch.dict(sys.modules["jeepney.io.blocking"].__dict__,
                             open_dbus_connection=mock.Mock(side_effect=OSError("no bus"))):
            env, err = self.run_claude()
        self.assertIn("couldn't read the wallet (no bus)", err)

    def test_locked_wallet_stores_and_forgets_nothing(self):
        self.wallet.locked = True
        code, _out, err = self.main("store", "claude", stdin=SECRET + "\n")
        self.assertIn("the wallet is locked", str(code))
        self.assertEqual(self.wallet.items, {})

    def test_forget(self):
        self.main("store", "claude", stdin=SECRET + "\n")
        self.assertEqual(self.main("forget", "claude")[:2], (0, "claude: token removed from the wallet.\n"))
        self.assertEqual(self.wallet.items, {})
        self.assertEqual(self.main("forget", "claude")[:2], (0, ""))       # (none: nothing to say)
        self.assertEqual(self.main("status", "claude")[:2], (1, "none\n"))

    def test_what_isnt_a_token_isnt_stored(self):
        for wrong in ("", "short", "sk-ant oat01 with spaces in it", "é" * 30):
            code, _out, _err = self.main("store", "claude", stdin=wrong + "\n")
            self.assertIn("isn't a token", str(code))
        self.assertEqual(self.wallet.items, {})

    def test_other_commands_and_usage_are_refused(self):
        for args in (("run", "rg", "/bin/rg"), ("store", "gh"), ("run", "claude"), ("nosuch", "claude")):
            code = self.main(*args)[0]
            self.assertIn("wallet-token run claude REAL", str(code))
        self.assertEqual(self.wallet.opened, 0)


class YesInYourLanguage(unittest.TestCase):
    """wallet-tool's yes/no questions: [y/N] in the reader's language, whose first letter is that
    language's yes ([s/N] in Spanish): it counts as yes, and so does y; Enter is the default."""

    def answer(self, typed, default, keys):
        import builtins
        import importlib.machinery
        import importlib.util
        from unittest import mock
        loader = importlib.machinery.SourceFileLoader("wallet_tool", str(TOOL))
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
        loader.exec_module(mod)
        asked = []
        with mock.patch.object(mod, "_", lambda text: keys.get(text, text)), \
                mock.patch.object(builtins, "input", lambda q: asked.append(q) or typed):
            return mod.yes("Move it?", default), asked[0]

    def test_spanish_letters_and_y(self):
        es = {"[y/N]": "[s/N]", "[Y/n]": "[S/n]"}
        self.assertEqual(self.answer("sí", False, es), (True, "Move it? [s/N] "))
        self.assertEqual(self.answer("y", False, es)[0], True)
        self.assertEqual(self.answer("n", True, es), (False, "Move it? [S/n] "))
        self.assertEqual(self.answer("", True, es)[0], True)
        self.assertEqual(self.answer("", False, es)[0], False)

    def test_english(self):
        self.assertEqual(self.answer("yes", False, {}), (True, "Move it? [y/N] "))
        self.assertEqual(self.answer("s", False, {})[0], False)


if __name__ == "__main__":
    unittest.main()
