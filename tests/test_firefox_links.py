"""Firefox privacy (packs/core/firefox) never follows a link in Firefox's own folder, which
Firefox's sandbox can write while the tweak runs outside it: a backup, prefs.js or user.js that
leads elsewhere, and a profile path (installs.ini) or profile folder leading out of Firefox's
folder, are refused, and nothing outside that folder is written or copied in. Nor does a FIFO
there keep it, or its status check, waiting. In a throwaway home, with Firefox not running."""
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
FIREFOX = ROOT / "packs/core/firefox"
SECRET = "the contents of a file of yours\n"


class FirefoxLinks(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.app = self.home / ".var/app/org.mozilla.firefox"
        self.root = self.app / ".mozilla/firefox"
        self.profile = self.root / "abc.default-release"
        self.profile.mkdir(parents=True)
        (self.root / "installs.ini").write_text("[X]\nDefault=abc.default-release\n")
        self.stubs = self.home / "stubs"
        stub(self.stubs, "pgrep", "exit 1")                    # Firefox isn't running
        # (files of yours, outside Firefox's folder)
        self.bashrc = self.home / ".bashrc"
        self.bashrc.write_text("# your .bashrc\n")
        self.secret = self.home / "secret.txt"
        self.secret.write_text(SECRET)

    def run_script(self, name, timeout=60):
        return subprocess.run(["bash", str(FIREFOX / name)], env=sandbox_env(self.home, self.stubs),
                              capture_output=True, text=True, timeout=timeout)

    def everything_under(self, folder):
        return "".join(p.read_text(errors="replace") for p in Path(folder).rglob("*") if p.is_file() and not p.is_symlink())

    def test_a_backup_link_isnt_written_through(self):
        """Uninstalling copied prefs.js over prefs.js.frame-tweaks-bak: planted as a link to your
        .bashrc, with a command in prefs.js, it made the .bashrc that command (cp follows it)."""
        self.assertEqual(self.run_script("install.sh").returncode, 0)
        (self.profile / "prefs.js").write_text('user_pref("privacy.resistFingerprinting", true);\ntouch ~/pwned\n')
        (self.profile / "prefs.js.frame-tweaks-bak").symlink_to(self.bashrc)
        r = self.run_script("uninstall.sh")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("prefs.js.frame-tweaks-bak is a link, or not a plain file", r.stderr)
        self.assertEqual(self.bashrc.read_text(), "# your .bashrc\n")
        self.assertTrue((self.profile / "prefs.js.frame-tweaks-bak").is_symlink())    # (left alone)

    def test_a_prefs_js_link_isnt_copied_into_the_profile(self):
        """prefs.js as a link to a file of yours: its contents went into the backup and prefs.js,
        where Firefox reads them."""
        self.assertEqual(self.run_script("install.sh").returncode, 0)
        (self.profile / "prefs.js").symlink_to(self.secret)
        r = self.run_script("uninstall.sh")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("prefs.js is a link, or not a plain file", r.stderr)
        self.assertNotIn(SECRET, self.everything_under(self.app))
        self.assertEqual(self.secret.read_text(), SECRET)

    def test_a_user_js_link_is_refused(self):
        """user.js as a link to a file of yours: its contents were copied into a user.js of
        Firefox's, or (installed) the block went into your file."""
        (self.profile / "user.js").symlink_to(self.secret)
        for script in ("install.sh", "uninstall.sh"):
            r = self.run_script(script)
            self.assertNotEqual(r.returncode, 0, script)
            self.assertIn("user.js is a link, or not a plain file", r.stderr)
            self.assertEqual(self.secret.read_text(), SECRET)
            self.assertNotIn(SECRET, self.everything_under(self.app))
            self.assertTrue((self.profile / "user.js").is_symlink())

    def test_a_profile_path_out_of_firefoxs_folder_is_refused(self):
        """installs.ini names the profile: through .., from /, or a profile folder that's a link,
        it led to a folder of yours (autostart, say), where user.js and the backup were written."""
        autostart = self.home / ".config/autostart"
        autostart.mkdir(parents=True)
        (self.profile / "prefs.js").write_text('user_pref("x", 1);\n')
        link = self.root / "elsewhere.default"
        link.symlink_to(autostart)
        for default in ("../../../../../.config/autostart", str(autostart), "elsewhere.default",
                        "abc.default-release/../../../../../../.config/autostart"):
            with self.subTest(default=default):
                (self.root / "installs.ini").write_text(f"[X]\nDefault={default}\n")
                for script in ("install.sh", "uninstall.sh"):
                    r = self.run_script(script)
                    self.assertNotEqual(r.returncode, 0, script)
                    self.assertIn("isn't a folder inside Firefox's own", r.stderr)
                    self.assertEqual(list(autostart.iterdir()), [])

    def test_firefoxs_profiles_folder_leading_out_is_refused(self):
        """The folder of profiles itself a link out of Firefox's folder (its sandbox can make one):
        refused, as a profile path is."""
        elsewhere = self.home / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "abc.default-release").mkdir()
        (elsewhere / "installs.ini").write_text("[X]\nDefault=abc.default-release\n")
        os.rename(self.root, self.app / "old")
        self.root.symlink_to(elsewhere)
        r = self.run_script("install.sh")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("isn't a folder inside Firefox's own", r.stderr)
        self.assertEqual(sorted(p.name for p in (elsewhere / "abc.default-release").iterdir()), [])

    def test_installs_ini_as_a_link_is_refused(self):
        (self.root / "installs.ini").unlink()
        (self.root / "installs.ini").symlink_to(self.secret)
        r = self.run_script("install.sh")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("installs.ini is a link, or not a plain file", r.stderr)

    def test_written_by_renaming_a_new_file_over_the_old(self):
        """user.js and prefs.js are replaced, not written into (a link put in their place between
        the check and the write would be replaced, not followed): a new file each time, yours
        only."""
        (self.profile / "user.js").write_text('user_pref("mine", 1);\n')
        before = (self.profile / "user.js").stat().st_ino
        self.assertEqual(self.run_script("install.sh").returncode, 0)
        js = self.profile / "user.js"
        self.assertNotEqual(js.stat().st_ino, before)
        self.assertEqual(js.stat().st_mode & 0o777, 0o600)
        self.assertIn('user_pref("mine", 1);', js.read_text())
        self.assertEqual([p.name for p in self.profile.iterdir() if p.name.startswith(".")], [])   # (no leftovers)

    def test_a_fifo_doesnt_keep_it_waiting(self):
        """A FIFO (which the sandbox can make) at user.js or prefs.js: reading it waited for good,
        and with it every update (which installs each tweak again) and status check. Now it's
        refused, or (the status check) taken as no file."""
        self.assertEqual(self.run_script("install.sh").returncode, 0)
        for name, scripts in (("user.js", ("install.sh", "uninstall.sh")), ("prefs.js", ("uninstall.sh",))):
            with self.subTest(name=name):
                f = self.profile / name
                before = f.read_text() if f.exists() else None
                f.unlink(missing_ok=True)
                os.mkfifo(f)
                for script in scripts:
                    r = self.run_script(script, timeout=20)
                    self.assertNotEqual(r.returncode, 0, script)
                    self.assertIn(f"{name} is a link, or not a plain file", r.stderr)
                r = self.run_script("status.sh", timeout=20)
                self.assertEqual(r.returncode, 1 if name == "user.js" else 2, r.stdout + r.stderr)
                f.unlink()
                if before is not None:
                    f.write_text(before)

    def test_a_fifo_switched_in_after_the_check_doesnt_either(self):
        """user.js switched between a file and a FIFO, as the sandbox can keep doing: one there
        when it's opened, just after the check, isn't waited on either. (A couple of seconds.)"""
        stop = threading.Event()

        def switch():
            i = 0
            while not stop.is_set():
                tmp = self.profile / f".u{i % 2}"
                tmp.unlink(missing_ok=True)
                if i % 2:
                    os.mkfifo(tmp)
                else:
                    tmp.write_text("// yours\n")
                os.rename(tmp, self.profile / "user.js")
                i += 1
        t = threading.Thread(target=switch)
        t.start()
        try:
            end = time.monotonic() + 2
            while time.monotonic() < end:
                self.run_script("install.sh", timeout=10)        # (TimeoutExpired: it waited)
        finally:
            stop.set()
            t.join()

    def test_a_refused_uninstall_leaves_the_profile_as_it_was(self):
        """A backup link found while uninstalling: our settings had already gone from user.js
        (and the message said the profile was left alone)."""
        self.assertEqual(self.run_script("install.sh").returncode, 0)
        js = (self.profile / "user.js").read_text()
        (self.profile / "prefs.js").write_text('user_pref("privacy.resistFingerprinting", true);\n')
        (self.profile / "prefs.js.frame-tweaks-bak").symlink_to(self.bashrc)
        r = self.run_script("uninstall.sh")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("prefs.js.frame-tweaks-bak is a link, or not a plain file", r.stderr)
        self.assertEqual((self.profile / "user.js").read_text(), js)
        self.assertNotIn("Removed our settings", r.stdout)

    def test_a_profile_link_switched_while_going_in(self):
        """A profile that's a link the sandbox keeps switching between a folder inside and one
        outside: cd -P works out where it went from the path, after going in, so it could go into
        the one outside and still say it was inside, then write user.js there. (Runs until it's
        been tried often enough to catch that: a few seconds.)"""
        outside = self.home / "outside"
        outside.mkdir()
        (self.root / "inside").mkdir()
        (self.root / "installs.ini").write_text("[X]\nDefault=l\n")
        stop = threading.Event()

        def switch():
            i = 0
            while not stop.is_set():
                tmp = self.root / f".l{i % 2}"
                tmp.unlink(missing_ok=True)
                tmp.symlink_to(outside if i % 2 == 0 else "inside")
                os.rename(tmp, self.root / "l")
                i += 1
        t = threading.Thread(target=switch)
        t.start()
        try:
            end = time.monotonic() + 3
            runs = 0
            while time.monotonic() < end and not any(outside.iterdir()):
                self.run_script("install.sh")
                runs += 1
        finally:
            stop.set()
            t.join()
        self.assertEqual(sorted(p.name for p in outside.iterdir()), [], f"after {runs} runs")


if __name__ == "__main__":
    unittest.main()
