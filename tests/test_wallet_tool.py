"""wallet-tool (packs/core/wallet): terminal tools from Homebrew behind the shared KDE wallet. It
offers the commands of the formulae you installed (brew leaves) and of casks, not those of
dependencies, Homebrew itself or gh (the Wallet install's own wrapper); protecting writes a
wrapper in ~/.local/bin that runs the real command through with-keyring; --list and --remove
follow; a program of yours there is never overwritten or removed. A fake Homebrew prefix stands
in for /home/linuxbrew/.linuxbrew."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, sandbox_env, stub  # noqa: E402

TOOL = ROOT / "packs/core/wallet/wallet-tool"


class WalletTool(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        t = Path(tmp.name)
        self.home, prefix = t / "home", t / "linuxbrew"
        self.prefix = prefix
        for owner, cmd in (("Caskroom/claude-code@latest/2.1", "claude"), ("Cellar/ripgrep/14.1/bin", "rg"),
                           ("Cellar/pcre2/10.4/bin", "pcre2grep"), ("Cellar/gh/2.80/bin", "gh")):
            stub(prefix / owner, cmd, f'echo "real {cmd} $*"')
            (prefix / "bin").mkdir(parents=True, exist_ok=True)
            (prefix / "bin" / cmd).symlink_to(prefix / owner / cmd)
        stub(prefix / "bin", "brew", 'case "$1" in leaves) printf "ripgrep\\ngh\\n" ;; esac')
        # (with-keyring: just runs the command, saying it did)
        stub(self.home / ".local/bin", "with-keyring", 'echo "with-keyring"; exec "$@"')
        self.env = sandbox_env(self.home, FRAME_TWEAKS_BREW=prefix / "bin/brew")

    def tool(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(TOOL), *args], env=self.env, capture_output=True, text=True, timeout=30)
        if ok is not None:
            self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def listed(self, arg):
        return dict(line.split("\t", 1) for line in self.tool(arg).stdout.splitlines())

    def test_offers_what_you_installed_not_dependencies_brew_or_gh(self):
        self.assertEqual(self.listed("--candidates"), {"claude": "claude-code@latest", "rg": "ripgrep"})

    def test_protect_runs_it_through_with_keyring_then_remove(self):
        self.tool("claude")
        wrapper = self.home / ".local/bin/claude"
        self.assertTrue(os.access(wrapper, os.X_OK))
        r = subprocess.run([str(wrapper), "doctor"], env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.stdout.split("\n")[:2], ["with-keyring", "real claude doctor"])
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


if __name__ == "__main__":
    unittest.main()
