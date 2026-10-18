"""The sudo password a tweak asks for isn't left for anything else to use without asking: Battery
charge limit's udev rule (adding and removing it) is one sudo command that remembers nothing
(sudo -k COMMAND), so nothing running meanwhile can use it either; it's forgotten (sudo -k) right
after Homebrew's installer (need_brew), and before and after each tweak's script in an install,
uninstall or reinstall run (its migration too), so nothing that runs later (what the tweak runs
next, the next tweak, a status check) can use it. A stand-in sudo, first on PATH, records its
calls and keeps a "remembered password" as sudo does: -v makes one, -k forgets it, -n uses it.
In a throwaway home: nothing real is asked for or run as root."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
CHARGE = ROOT / "packs/core/charge-limit"
# sudo: -v remembers the password (a file), -k forgets it, -n COMMAND runs only while it's
# remembered. COMMAND alone asks for it and remembers it, -k COMMAND asks for it and doesn't. A
# COMMAND (sh, tee, rm, chown) is run as you, with files in the throwaway home only; "remembered
# while it ran" in the log: anything else could have used the password meanwhile. ($SUDO_FAIL:
# forget, sudo -k alone fails; run, every COMMAND fails, as with a wrong password.)
SUDO = r'''echo "sudo $*" >> "$HOME/sudo.log"
run() {
    if [ -f "$HOME/remembered" ]; then echo "  remembered while it ran" >> "$HOME/sudo.log"; fi
    [ "${SUDO_FAIL:-}" = run ] && exit 1
    for a; do case "$a" in /*) case "$a" in "$HOME"/*) ;; *) exit 1 ;; esac ;; esac; done
    case "$1" in sh|tee|rm|chown) exec "$@" ;; esac
    exit 1
}
case "$1" in
    -v) touch "$HOME/remembered" ;;
    -k|-K) if [ $# -eq 1 ]; then [ "${SUDO_FAIL:-}" = forget ] && exit 1; rm -f "$HOME/remembered"; exit 0; fi
           shift; run "$@" ;;
    -n) [ -f "$HOME/remembered" ] || { echo "sudo: a password is required" >&2; exit 1; }; shift; exec "$@" ;;
    *) touch "$HOME/remembered"; run "$@" ;;
esac'''


class Home(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.stubs = self.home / "stubs"
        stub(self.stubs, "sudo", SUDO)
        stub(self.stubs, "passwd", 'echo "$2 P 2026-01-01 0 99999 7 -1"')     # (has a password)
        stub(self.stubs, "systemctl", "exit 0")

    def sudo_calls(self):
        log = self.home / "sudo.log"
        return log.read_text().splitlines() if log.exists() else []

    def remembered(self):
        return (self.home / "remembered").exists()


class ChargeLimit(Home):
    """Its install.sh and uninstall.sh, copied with their system paths in the throwaway home (and
    the installed programs left out: the copy stops right after the udev rule)."""
    def script(self, name):
        etc = self.home / "etc"
        etc.mkdir(exist_ok=True)
        self.rule, self.keep, self.switch = etc / "rule", etc / "keep", self.home / "charging_pause"
        self.switch.write_text("0\n")
        src = (CHARGE / name).read_text()
        for old, new in (("/sys/class/power_supply/pm8550b-charger/charging_pause", self.switch),
                         ("/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules", self.rule),
                         ("/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf", self.keep),
                         ("$XDG_RUNTIME_DIR_USER/charge-limit/paused", self.home / "run/charge-limit/paused")):
            self.assertEqual(src.count(old), 1 if name == "uninstall.sh" or "paused" not in old else 0, old)   # (never the real ones)
            src = src.replace(old, str(new))
        d = self.home / "tweak"
        d.mkdir(exist_ok=True)
        shutil.copy(CHARGE / "charge-limit.rules", d)
        stub(d, "check-system.sh", "exit 0")
        (d / name).write_text(src)
        return d / name

    def run_script(self, path, **env):
        return subprocess.run(["bash", str(path)], env=sandbox_env(self.home, self.stubs, FRAME_TWEAKS_LIB=ROOT / "lib", **env),
                              capture_output=True, text=True, timeout=60)

    def privileged(self, calls):
        """The calls that ran something as root (not -v, -k alone or -n)."""
        return [c for c in calls if c.startswith("sudo ") and c not in ("sudo -v", "sudo -k") and not c.startswith("sudo -n ")]

    def test_install_asks_once_and_leaves_nothing_remembered(self):
        """sudo -v, then three sudo commands that used the password it remembered: anything left
        running in this terminal (by a tweak before it, say) could use it meanwhile too."""
        for fail in ("", "run"):                   # (added, or adding it failed)
            with self.subTest(fail=fail):
                (self.home / "sudo.log").unlink(missing_ok=True)
                script = self.script("install.sh")
                self.rule.unlink(missing_ok=True)          # (not there yet: it asks)
                r = self.run_script(script, SUDO_FAIL=fail)
                calls = self.sudo_calls()
                self.assertNotIn("  remembered while it ran", calls)
                self.assertNotIn("sudo -v", calls)
                self.assertEqual(len(self.privileged(calls)), 1, calls)
                self.assertTrue(self.privileged(calls)[0].startswith("sudo -k "), calls)
                self.assertEqual(calls[-1], "sudo -k", calls)
                self.assertFalse(self.remembered(), r.stdout + r.stderr)
                if fail:
                    self.assertIn("Couldn't add the udev rule", r.stderr)
                else:
                    self.assertIn("ACTION==", self.rule.read_text())
                    self.assertEqual(self.keep.read_text(), f"{self.rule}\n")
                    self.assertIn(f" {os.getuid()} {self.switch}\n", (self.home / "sudo.log").read_text())   # (the switch)

    def test_uninstall_asks_once_and_leaves_nothing_remembered(self):
        for fail in ("", "run"):
            with self.subTest(fail=fail):
                (self.home / "sudo.log").unlink(missing_ok=True)
                script = self.script("uninstall.sh")
                self.rule.write_text("rule\n")
                self.keep.write_text(f"{self.rule}\n")
                r = self.run_script(script, SUDO_FAIL=fail)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                calls = self.sudo_calls()
                self.assertNotIn("  remembered while it ran", calls)
                self.assertEqual(len(self.privileged(calls)), 1, calls)
                self.assertTrue(self.privileged(calls)[0].startswith("sudo -k "), calls)
                self.assertEqual(calls[-1], "sudo -k", calls)
                self.assertFalse(self.remembered())
                self.assertEqual(self.rule.exists() or self.keep.exists(), bool(fail))
                self.assertIn("Left its udev rule" if fail else f"removed {self.rule}", r.stdout + r.stderr)

    def test_a_sudo_that_cant_forget_doesnt_stop_it(self):
        """(sudo -k failing, in a script that stops at a failing command: it went on as before)"""
        script = self.script("uninstall.sh")
        self.rule.write_text("rule\n")
        r = self.run_script(script, SUDO_FAIL="forget")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"removed {self.rule}", r.stdout)


class NeedBrew(Home):
    """need_brew with no Homebrew: a stand-in for its installer (which uses sudo, as Homebrew's
    does) instead of the download; afterwards, what the tweak runs next can't use the password."""
    def run_need_brew(self, installer_ok=True):
        brew = self.home / "linuxbrew/bin/brew"
        installer = self.home / "brew-installer.sh"
        installer.write_text('sudo -n true && echo "installer used sudo" >> "$HOME/log"\n'
                             + (f"mkdir -p {brew.parent} && echo '#!/bin/sh' > {brew} && chmod +x {brew}\n"
                                if installer_ok else "exit 1\n"))
        script = self.home / "need-brew.sh"
        script.write_text(f'source {ROOT / "lib/common.sh"}\n'
                          f'BREW={brew}\n'
                          'ask() { return 0; }                          # (yes, install it)\n'
                          f'fetch_pinned() {{ cp {installer} "$2"; }}     # (no download)\n'
                          'need_brew\n'
                          'sudo -n true && echo "used it afterwards" >> "$HOME/log"\n'
                          'echo done >> "$HOME/log"\n')
        r = subprocess.run(["bash", str(script)], env=sandbox_env(self.home, self.stubs), capture_output=True, text=True,
                           timeout=60)
        log = self.home / "log"
        return r, log.read_text().splitlines() if log.exists() else []

    def test_the_password_is_forgotten_after_homebrews_installer(self):
        r, log = self.run_need_brew()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(log, ["installer used sudo", "done"])
        self.assertEqual(self.sudo_calls(), ["sudo -v", "sudo -n true", "sudo -k", "sudo -n true"])
        self.assertFalse(self.remembered())

    def test_and_when_the_installer_fails(self):
        r, log = self.run_need_brew(installer_ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Homebrew's installer failed", r.stderr)
        self.assertEqual(self.sudo_calls()[-1], "sudo -k")
        self.assertFalse(self.remembered())


README = """---
title: {title}
emoji: 🧪
category: Tests
tier: extras
summary: A test tweak
what: Uses sudo, or tries to.
why: For tests.
author: Tests
changes: Nothing
access: None
survives_updates: "Yes"
undo: ./install.sh uninstall {id}
---
# {title}
"""
# primer asks for the password (sudo -v); other uses it only if it's still remembered (sudo -n),
# in its install, uninstall, migration and status.
SCRIPTS = {
    "primer": {"install.sh": "sudo -v", "uninstall.sh": "sudo -v", "migrate.sh": "sudo -v",
               "status.sh": 'echo "ok       primer"'},
    "other": {"install.sh": 'sudo -n true && echo "other install: used it" >> "$HOME/log"; exit 0',
              "uninstall.sh": 'sudo -n true && echo "other uninstall: used it" >> "$HOME/log"; exit 0',
              "migrate.sh": 'sudo -n true && echo "other migration: used it" >> "$HOME/log"; exit 0',
              "status.sh": 'sudo -n true && echo "other status: used it" >> "$HOME/log"; echo "ok       other"'},
}


class InstallRun(Home):
    """install.sh install/uninstall with two tweaks from a trusted test pack: one asks for the
    password, the one after it (or the status checks after the run) can't use it."""
    def setUp(self):
        super().setUp()
        if not shutil.which("flock"):
            self.skipTest("needs flock")
        self.pack = self.home / "pack"
        for tid, scripts in SCRIPTS.items():
            d = self.pack / tid
            d.mkdir(parents=True)
            (d / "README.md").write_text(README.format(id=tid, title=tid.title()))
            for name, body in scripts.items():
                (d / name).write_text(f"#!/bin/bash\n{body}\n")
        (self.pack / "pack.md").write_text("---\nname: Sudo pack\napi: 1\n---\n")
        for tool in ("flatpak", "brew", "nmcli"):
            stub(self.stubs, tool, "exit 1")
        self.env = sandbox_env(self.home / "h", self.stubs, path=(os.path.dirname(shutil.which("flock")), "/usr/bin", "/bin"),
                               FRAME_TWEAKS_PACKS=self.pack, FRAME_TWEAKS_KEEP_CHECKOUT=1)
        (self.home / "h").mkdir()
        # (the official packs off: only these two run)
        off = self.home / "h/.config/frame-tweaks/installer/off-packs"
        off.parent.mkdir(parents=True)
        off.write_text("core\nintegrations\nthird-party\n")
        r = subprocess.run(["python3", str(ROOT / "lib/sft.py"), "mods", "trust", str(self.pack)], env=self.env,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def sh(self, *args):
        return subprocess.run([str(ROOT / "install.sh"), *args], env=self.env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=120)

    def log(self):
        p = self.home / "h/log"
        return p.read_text().splitlines() if p.exists() else []

    def remembered(self):
        return (self.home / "h/remembered").exists()

    def test_the_next_tweak_cant_use_the_password(self):
        for args in (("install", "primer", "other"), ("uninstall", "primer", "other"),
                     ("install", "other", "primer"),           # (primer last: then the status checks)
                     ("reinstall", "primer", "other")):        # (each removed, then each installed)
            with self.subTest(args=args):
                (self.home / "h/log").unlink(missing_ok=True)
                r = self.sh(*args)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(self.log(), [])
                self.assertFalse(self.remembered())

    def test_a_password_remembered_before_the_run_isnt_used_either(self):
        (self.home / "h/remembered").touch()               # (sudo typed in this terminal just before)
        r = self.sh("install", "other")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), [])

    def test_nor_by_a_migration(self):
        """An install or update first runs the migrate.sh of each tweak installed by an older
        release: they ran before the first sudo -k, with a password remembered before the run, or
        one the migration before asked for."""
        state = self.home / "h/.local/state/frame-tweaks/installed"
        for ids, before in ((("other",), True), (("primer", "other"), False)):
            with self.subTest(ids=ids, remembered_before=before):
                state.mkdir(parents=True, exist_ok=True)
                for tid in SCRIPTS:
                    (state / tid).write_text("0.1.0\n")          # (installed by an older release)
                (self.home / "h/log").unlink(missing_ok=True)
                if before:
                    (self.home / "h/remembered").touch()
                r = self.sh("install", *ids)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("migrating other from 0.1.0", r.stdout)
                self.assertEqual(self.log(), [])
                self.assertFalse(self.remembered())


if __name__ == "__main__":
    unittest.main()
