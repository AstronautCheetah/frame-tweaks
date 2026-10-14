"""install.sh's own state, in a throwaway home with a trusted test pack whose one tweak ("probe")
only logs to a file there: installed/<id> records the version, migrate.sh runs (with the old
version) only when that record is older, hold/unhold and held tweaks being left alone during
updates (FRAME_TWEAKS_UPDATING=1), and the lock refusing a second run."""
import fcntl
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text().strip()

README = """\
---
title: Probe
emoji: 🧪
category: Tests
tier: extras
summary: A test tweak that only logs
what: Logs what the installer runs.
why: For tests.
author: Tests
changes: A log file in the home folder
access: None
survives_updates: "Yes"
undo: ./install.sh uninstall probe
processes: []
---
# Probe
"""
SCRIPTS = {
    "install.sh": 'echo install >> "$HOME/probe.log"; touch "$HOME/probe-installed"',
    "uninstall.sh": 'echo uninstall >> "$HOME/probe.log"; rm -f "$HOME/probe-installed"',
    "status.sh": '[ -f "$HOME/probe-installed" ] && { echo "ok       installed"; exit 0; }; echo "missing  no"; exit 1',
    "migrate.sh": 'echo "migrate $1" >> "$HOME/probe.log"',
}


class InstallState(unittest.TestCase):
    def setUp(self):
        if not shutil.which("flock"):
            self.skipTest("needs flock")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.home = t / "home"
        self.home.mkdir()
        self.pack = t / "probe-pack"
        d = self.pack / "probe"
        d.mkdir(parents=True)
        (self.pack / "pack.md").write_text("---\nname: Probe pack\napi: 1\n---\n")
        (d / "README.md").write_text(README)
        for name, body in SCRIPTS.items():
            (d / name).write_text(f"#!/bin/bash\n{body}\n")
        self.env = {"HOME": str(self.home), "USER": os.environ.get("USER", "u"), "LANG": "C.UTF-8",
                    "PATH": os.pathsep.join([os.path.dirname(shutil.which("flock")), "/usr/bin", "/bin"]),
                    "FRAME_TWEAKS_PACKS": str(self.pack)}
        r = subprocess.run(["python3", str(ROOT / "lib/sft.py"), "mods", "trust", str(self.pack)],
                           env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.state = self.home / ".local/state/frame-tweaks"
        self.record = self.state / "installed/probe"

    def sh(self, *args, **extra):
        return subprocess.run([str(ROOT / "install.sh"), *args], env={**self.env, **extra}, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=120)

    def log(self):
        p = self.home / "probe.log"
        return p.read_text().split("\n")[:-1] if p.exists() else []

    def installed_at(self, version):
        self.record.parent.mkdir(parents=True, exist_ok=True)
        self.record.write_text(version + "\n")
        (self.home / "probe-installed").touch()

    def test_install_records_the_version(self):
        r = self.sh("install", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.record.read_text(), VERSION + "\n")
        self.assertEqual(self.log(), ["install"])

    def test_reinstall_at_the_same_version_doesnt_migrate(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        r = self.sh("install", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), ["install", "install"])

    def test_older_record_migrates_first_with_the_old_version(self):
        self.installed_at("0.0.1")
        r = self.sh("install", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), ["migrate 0.0.1", "install"])
        self.assertIn("migrating probe from 0.0.1", r.stdout)
        self.assertEqual(self.record.read_text(), VERSION + "\n")

    def test_newer_record_doesnt_migrate_backwards(self):
        self.installed_at("99.0.0")              # going back to an older Frame Tweaks
        r = self.sh("install", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), ["install"])

    def test_never_installed_doesnt_migrate(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.assertNotIn("migrate", " ".join(self.log()))

    def test_uninstall_forgets_the_version(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        r = self.sh("uninstall", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(self.record.exists())

    def test_hold_and_unhold(self):
        r = self.sh("hold", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.state / "held/probe").is_file())
        r = self.sh("unhold", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.state / "held/probe").exists())

    def test_hold_refuses_an_unknown_id(self):
        r = self.sh("hold", "no-such-tweak")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown component", r.stderr)
        self.assertFalse((self.state / "held/no-such-tweak").exists())

    def test_held_tweak_is_left_alone_during_an_update(self):
        self.installed_at("0.0.1")
        self.assertEqual(self.sh("hold", "probe").returncode, 0)
        r = self.sh("install", "probe", FRAME_TWEAKS_UPDATING="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("held: left as it is", r.stdout)
        self.assertEqual(self.log(), [])                        # neither migrated nor reinstalled
        self.assertEqual(self.record.read_text(), "0.0.1\n")

    def test_held_tweak_still_migrates_when_installed_by_hand(self):
        self.installed_at("0.0.1")
        self.assertEqual(self.sh("hold", "probe").returncode, 0)
        r = self.sh("install", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), ["migrate 0.0.1", "install"])

    def test_unheld_tweak_migrates_during_an_update(self):
        self.installed_at("0.0.1")
        self.sh("hold", "probe")
        self.sh("unhold", "probe")
        r = self.sh("install", "probe", FRAME_TWEAKS_UPDATING="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), ["migrate 0.0.1", "install"])

    def test_lock_refuses_a_second_run(self):
        self.state.mkdir(parents=True)
        with open(self.state / "install.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)       # another run holds it
            r = self.sh("install", "probe")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("Another Frame Tweaks install", r.stderr)
            self.assertEqual(self.log(), [])
        r = self.sh("install", "probe")                           # released: runs again
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), ["install"])


if __name__ == "__main__":
    unittest.main()
