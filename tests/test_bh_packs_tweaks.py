"""Integrations, 3rd Party and small Core tweaks, run in a throwaway home with stand-ins for
system tools: Firefox's user.js block (a last line without a newline, a start marker without its
end), NordVPN's reinstall keeping the VPN setup, Shared clipboard's build files staying in the
temporary folder, restart-plasmashell waiting for (or killing) the old taskbar, and the example
tweak's Run button going through its menu entry."""
import sys
import hashlib
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.stubs = self.home / "stubs"
        self.stubs.mkdir()

    def stub(self, name, body):
        stub(self.stubs, name, body)

    def run_path(self, path, *args, env=None):
        # (in English, whichever language an open installer window shows)
        full = sandbox_env(self.home, self.stubs, **(env or {}))
        return subprocess.run(["bash", str(path), *args], env=full, capture_output=True, text=True, timeout=60)

    def run_script(self, script, *args, env=None):
        return self.run_path(next(ROOT.glob("packs/*/" + script)), *args, env=env)


class FirefoxUserJs(Home):
    def setUp(self):
        super().setUp()
        root = self.home / ".var/app/org.mozilla.firefox/.mozilla/firefox"
        profile = root / "abc.default-release"
        profile.mkdir(parents=True)
        (root / "installs.ini").write_text("[X]\nDefault=abc.default-release\n")
        self.user_js = profile / "user.js"
        self.stub("pgrep", "exit 1")                      # Firefox isn't running

    def test_a_last_line_without_its_newline(self):
        # (as editors that don't add a final newline save it): the start marker gets its own line,
        # so the block is found again, replaced, and removed with nothing of it left
        self.user_js.write_text('user_pref("mine", 1);')
        for _run in range(2):
            r = self.run_script("firefox/install.sh")
            self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.user_js.read_text().splitlines()
        self.assertEqual(lines[:2], ['user_pref("mine", 1);', "// >>> frame-tweaks"])
        self.assertEqual(lines.count("// >>> frame-tweaks"), 1)
        r = self.run_script("firefox/uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.user_js.read_text(), 'user_pref("mine", 1);\n')

    def test_a_start_marker_without_its_end_changes_nothing(self):
        # sed would delete from the marker to the end of the file, the user's own lines too
        for text in ('// >>> frame-tweaks\nuser_pref("old", 1);\nuser_pref("mine", 2);\n',
                     '// >>> frame-tweaks\nuser_pref("mine", 2);\n// >>> frame-tweaks\nx\n// <<< frame-tweaks\n',
                     'user_pref("mine", 2);\n// >>> steam-frame-tweaks\nuser_pref("old", 1);\n'):
            self.user_js.write_text(text)
            for script in ("firefox/install.sh", "firefox/uninstall.sh"):
                r = self.run_script(script)
                self.assertNotEqual(r.returncode, 0, script)
                self.assertIn("fix that by hand", r.stderr)
                self.assertEqual(self.user_js.read_text(), text, script)

    def test_a_stray_end_marker_is_harmless(self):
        self.user_js.write_text('// <<< frame-tweaks\nuser_pref("mine", 1);\n')
        r = self.run_script("firefox/install.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('user_pref("mine", 1);', self.user_js.read_text())


class NordVPNUninstall(Home):
    """A reinstall (the ↻ button) replaces the programs and keeps the VPN setup (setting it up
    again takes a new access token); removing the tweak removes the setup too."""
    def setUp(self):
        super().setUp()
        self.calls = self.home / "calls.log"
        bin_dir = self.home / ".local/bin"
        bin_dir.mkdir(parents=True)
        for name in ("nordvpn-wg", "nordvpn-tray"):
            (bin_dir / name).write_text(f'#!/bin/sh\necho "{name} $*" >> {self.calls}\n')
            (bin_dir / name).chmod(0o755)
        self.conf = self.home / ".config/nordvpn-wg"
        self.conf.mkdir(parents=True)
        (self.conf / "private_key").write_text("key\n")
        self.venv = self.home / ".local/share/arrowpad/venv"
        (self.venv / "bin").mkdir(parents=True)
        self.stub("pkill", f'echo "pkill $*" >> {self.calls}')
        self.stub("nmcli", f'echo "nmcli $*" >> {self.calls}\n'
                           '[ "$*" = "-t -f TYPE,NAME connection show" ] && printf "wireguard:NordVPN Japan\\n"; exit 0')

    def calls_made(self):
        return self.calls.read_text() if self.calls.exists() else ""

    def test_reinstall_keeps_the_setup(self):
        r = self.run_script("nordvpn/uninstall.sh", env={"FRAME_TWEAKS_REINSTALL": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("connection delete", self.calls_made())
        self.assertNotIn("nordvpn-wg down", self.calls_made())         # still connected
        self.assertTrue((self.conf / "private_key").exists())
        self.assertTrue(self.venv.exists())                             # no 280 MB download again
        self.assertFalse((self.home / ".local/bin/nordvpn-wg").exists())   # the programs go

    def test_uninstall_removes_the_connections(self):
        r = self.run_script("nordvpn/uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nordvpn-wg down", self.calls_made())
        self.assertIn("nmcli connection delete NordVPN Japan", self.calls_made())
        self.assertTrue((self.conf / "private_key").exists())   # (its settings: install.sh keeps or removes them, ⚙ Preferences)
        self.assertFalse(self.venv.exists())

    def test_a_connection_that_wont_go_doesnt_stop_the_uninstall(self):
        # (it used to stop there when it was the last one, at every try)
        self.stub("nmcli", '[ "$*" = "-t -f TYPE,NAME connection show" ] && printf "wireguard:NordVPN Japan\\n"\n'
                           '[ "$2" = delete ] && { echo "Error: not allowed" >&2; exit 1; }; exit 0')
        r = self.run_script("nordvpn/uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not allowed", r.stderr)
        self.assertFalse((self.home / ".local/bin/nordvpn-tray").exists())


class ClipboardRelease(Home):
    """Shared clipboard installs Frame Tweaks' build of clipboard-sync: the pinned release, checked
    against the pin's SHA256 (a changed file is refused), and what older versions' builds on the
    Frame left (source, Rust's build folder) goes."""
    def setUp(self):
        super().setUp()
        import tarfile
        self.tweak = self.home / "clipboard"
        shutil.copytree(ROOT / "packs/integrations/clipboard", self.tweak)
        ver = re.search(r"(?m)^version=(.*)$", (self.tweak / "pin").read_text()).group(1)
        top = self.home / f"fixture/clipboard-sync-{ver}-aarch64-linux"
        top.mkdir(parents=True)
        (top / "clipboard-sync").write_text("#!/bin/sh\necho clipboard-sync\n")
        self.archive = self.home / "release.tar.gz"
        with tarfile.open(self.archive, "w:gz") as tar:
            tar.add(top, arcname=top.name)
        self.ver = ver
        self.stub("curl", f'while [ $# -gt 1 ]; do [ "$1" = -o ] && out=$2; shift; done; cp {self.archive} "$out"')
        self.stub("pgrep", "exit 1")                      # not in desktop mode: nothing started

    def install(self, sha):
        pin = re.sub(r"(?m)^sha256=.*$", f"sha256={sha}", (ROOT / "packs/integrations/clipboard/pin").read_text())
        (self.tweak / "pin").write_text(pin)
        return self.run_path(self.tweak / "install.sh", env={"FRAME_TWEAKS_LIB": str(ROOT / "lib"),
                                                             "FRAME_TWEAKS_DIRS": f"clipboard={self.tweak}"})

    def test_installs_the_pinned_release(self):
        old = self.home / ".local/share/frame-tweaks/src/clipboard-sync"
        (old / "target").mkdir(parents=True)                       # (an older version's build)
        (self.home / ".cache/frame-tweaks/rust-build").mkdir(parents=True)
        r = self.install(hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        root = self.home / ".local/share/frame-tweaks/clipboard-sync"
        self.assertEqual((root / "bin/clipboard-sync").read_text(), "#!/bin/sh\necho clipboard-sync\n")
        self.assertEqual((root / "VERSION").read_text(), self.ver + "\n")
        self.assertTrue((self.home / ".local/bin/clipboard-sync").is_symlink())
        self.assertFalse(old.exists())
        self.assertFalse((self.home / ".cache/frame-tweaks/rust-build").exists())

    def test_a_changed_file_is_refused(self):
        r = self.install("0" * 64)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.home / ".local/share/frame-tweaks/clipboard-sync/bin/clipboard-sync").exists())


class RestartPlasmashell(Home):
    """A new plasmashell quits at once while the old one still holds its D-Bus name, and a frozen
    one never acts on SIGTERM (it handles it in its event loop): so it waits for the old one to go,
    and kills it if it won't."""
    def setUp(self):
        super().setUp()
        # The desktop session's ksmserver, whose environment it starts plasmashell with.
        session = subprocess.Popen(["/bin/sleep", "60"], env={"PATH": f"{self.stubs}:/usr/bin:/bin", "HOME": str(self.home)})
        self.addCleanup(session.wait)
        self.addCleanup(session.kill)
        self.log = self.home / "log"
        # (its log in the test's folder, not the real /run/user/<uid>)
        self.script = self.home / "restart-plasmashell"
        self.script.write_text((ROOT / "packs/core/tools/restart-plasmashell").read_text()
                               .replace("/run/user/$(id -u)", str(self.home)))
        old, new = self.home / "old", self.home / "new"
        self.old = old
        # The old plasmashell: "ok" exits two seconds after SIGTERM, "frozen" only on SIGKILL.
        self.stub("pkill", f'[ -f {old} ] || exit 1\n'
                           f'case "$*" in *-KILL*) rm -f {old}; echo killed >> {self.log} ;; '
                           f'*) [ "$(cat {old})" = ok ] && echo 2 > {old}; echo stopping >> {self.log} ;; esac; exit 0')
        self.stub("sleep", f'[ -f {old} ] && n=$(cat {old}) && case $n in [1-9]) '
                           f'if [ "$n" = 1 ]; then rm -f {old}; else echo $((n - 1)) > {old}; fi ;; esac; exit 0')
        self.stub("pgrep", f'case "$*" in *ksmserver*) echo {session.pid} ;; '
                           f'*) [ -f {old} ] || [ -f {new} ] ;; esac')
        self.stub("setsid", f'if [ -f {old} ]; then echo "duplicate quit" >> {self.log}; '
                            f'else touch {new}; echo "started $*" >> {self.log}; fi')

    def restart(self, old_state):
        if old_state:
            self.old.write_text(old_state + "\n")
        r = self.run_path(self.script)
        return r, self.log.read_text() if self.log.exists() else ""

    def test_a_frozen_one_is_killed_then_replaced(self):
        r, log = self.restart("frozen")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("killed", log)
        self.assertIn("started -f plasmashell", log)
        self.assertNotIn("duplicate", log)
        self.assertLess(log.index("killed"), log.index("started"))

    def test_a_slow_one_is_waited_for(self):
        r, log = self.restart("ok")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("stopping", log)
        self.assertNotIn("killed", log)
        self.assertIn("started -f plasmashell", log)
        self.assertNotIn("duplicate", log)

    def test_none_running_just_starts_one(self):
        r, log = self.restart(None)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("started -f plasmashell", log)
        self.assertIn("plasmashell restarted", r.stdout)


class HelloFrameRun(Home):
    def test_run_goes_through_the_menu_entry(self):
        # (docs/mods.md: so a wallet gate on that entry applies)
        self.stub("gtk-launch", f'echo "$*" > {self.home}/launched')
        r = self.run_path(ROOT / "examples/hello-pack/hello-frame/run.sh", env={"FRAME_TWEAKS_LIB": str(ROOT / "lib")})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.home / "launched").read_text().strip(), "hello-frame")


if __name__ == "__main__":
    unittest.main()
