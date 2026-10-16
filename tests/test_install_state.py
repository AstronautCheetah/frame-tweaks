"""install.sh's own state, in a throwaway home with a trusted test pack whose one tweak ("probe")
only logs to a file there: installed/<id> records the version, migrate.sh runs (with the old
version) only when that record is older, hold/unhold and held tweaks being left alone during
updates (FRAME_TWEAKS_UPDATING=1), the lock refusing a second run, the last five logs kept (and
tweaks' own logs left alone), an uninstall keeping its settings or removing them (⚙ Preferences,
--remove-settings, and never on a reinstall), forget-settings deleting only what uninstalled
tweaks left, uninstall-self (every tweak or none, settings or not), a failed uninstall reported, and debug-info's report without names
and addresses. systemctl is a stand-in: sysctl_user would reach the real user session's systemd,
whatever HOME is."""
import sys
import fcntl
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
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
config: [~/.config/probe.conf, ~/.config/probe]
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
        self.stubs = t / "stubs"
        self.stubs.mkdir()
        self.stub("systemctl", 'case " $* " in *" is-active "*) exit 3 ;; esac')    # (nothing runs)
        # (and nothing machine-wide is reached: Flatpaks are the system's, Homebrew is shared)
        for tool in ("flatpak", "brew", "nmcli"):
            self.stub(tool, f'echo "{tool} $*" >> "$HOME/machine-wide.log"; exit 1')
        self.env = sandbox_env(self.home, self.stubs, path=(os.path.dirname(shutil.which("flock")), "/usr/bin", "/bin"),
                               FRAME_TWEAKS_PACKS=self.pack,
                               FRAME_TWEAKS_KEEP_CHECKOUT=1)    # (uninstall-self: never the checkout the tests run from)
        self.trust()
        # (every test: some official tweaks find what's installed machine-wide, a system
        # Flatpak say, and an "uninstall all" here once removed one for real)
        self.only_the_probe()
        self.state = self.home / ".local/state/frame-tweaks"
        self.record = self.state / "installed/probe"

    def tearDown(self):
        log = self.home / "machine-wide.log"
        self.assertFalse(log.exists(), log.read_text() if log.exists() else "")

    def stub(self, name, body):
        stub(self.stubs, name, body)

    def trust(self):
        """(again after changing the probe: trust is for the pack's files as they are)"""
        r = subprocess.run(["python3", str(ROOT / "lib/sft.py"), "mods", "trust", str(self.pack)],
                           env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def only_the_probe(self):
        """Turn the official packs off, for commands that would otherwise run all their tweaks'
        scripts (install all, debug-info's status), and make sure the probe is all that's left."""
        off = self.home / ".config/frame-tweaks/installer/off-packs"
        off.parent.mkdir(parents=True, exist_ok=True)
        off.write_text("integrations\noriginal\nthird-party\n")
        r = self.sh("_deps", "all")
        self.assertEqual(r.stdout.split(), ["probe"], r.stdout + r.stderr)

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

    def test_a_tweak_this_frame_doesnt_need_isnt_installed(self):
        """needed.sh exit 1: SteamOS does it itself, say. install skips it (all too) and list says
        why; installed already, it's still reinstalled (an update), and needed.sh exit 0 installs."""
        (self.pack / "probe/needed.sh").write_text("#!/bin/bash\necho 'SteamOS does it now'\nexit 1\n")
        self.trust()
        for args in (("install", "probe"), ("install", "all")):
            r = self.sh(*args)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Not needed on this Frame, so not installed: SteamOS does it now", r.stdout)
        self.assertEqual(self.log(), [])
        self.assertFalse(self.record.exists())
        self.assertIn("(not needed on this Frame: SteamOS does it now)", self.sh("list").stdout)
        self.installed_at(VERSION)
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.assertEqual(self.log(), ["install"])
        self.record.unlink()
        (self.pack / "probe/needed.sh").write_text("#!/bin/bash\nexit 0\n")
        self.trust()
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.assertEqual(self.log(), ["install", "install"])
        self.assertNotIn("not needed", self.sh("list").stdout)

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

    def settings_made(self):
        (self.home / ".config/probe").mkdir(parents=True)
        (self.home / ".config/probe/state.json").write_text("{}")
        (self.home / ".config/probe.conf").write_text("A=1\n")
        (self.home / ".config/other.conf").write_text("not the probe's\n")

    def test_uninstall_keeps_settings_by_default(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.settings_made()
        r = self.sh("uninstall", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.home / ".config/probe.conf").exists())
        self.assertTrue((self.home / ".config/probe/state.json").exists())
        self.assertIn("Kept its settings: ~/.config/probe.conf ~/.config/probe", r.stdout)
        self.assertIn("--remove-settings probe", r.stdout)

    def test_uninstall_removes_settings_when_the_preferences_say_so(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.settings_made()
        p = subprocess.run(["python3", str(ROOT / "lib/sft.py"), "uninstall-settings", "remove"],
                           env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.stdout.strip(), "remove", p.stderr)
        self.assertEqual((self.home / ".config/frame-tweaks/uninstall-settings").read_text(), "remove\n")
        r = self.sh("uninstall", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / ".config/probe.conf").exists())
        self.assertFalse((self.home / ".config/probe").exists())
        self.assertTrue((self.home / ".config/other.conf").exists())       # only what it lists
        self.assertNotIn("Kept its settings", r.stdout)
        # --keep-settings, for one run, over the preference
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        (self.home / ".config/probe.conf").write_text("A=1\n")
        r = self.sh("uninstall", "--keep-settings", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.home / ".config/probe.conf").exists())

    def test_remove_settings_option_and_reinstall(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.settings_made()
        r = self.sh("reinstall", "probe")                     # (a reinstall keeps them, whatever the preference)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.home / ".config/probe.conf").exists())
        r = self.sh("uninstall", "--remove-settings", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / ".config/probe.conf").exists())
        self.assertFalse((self.home / ".config/probe").exists())

    def test_forget_settings_takes_only_what_uninstalled_tweaks_left(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.settings_made()
        r = self.sh("forget-settings")                          # (installed: its settings are in use)
        self.assertIn("No settings left behind", r.stdout)
        self.assertTrue((self.home / ".config/probe.conf").exists())
        self.assertEqual(self.sh("uninstall", "probe").returncode, 0)
        r = self.sh("forget-settings", "--list")
        self.assertIn("probe\t~/.config/probe.conf", r.stdout)
        self.assertTrue((self.home / ".config/probe.conf").exists())
        r = self.sh("forget-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / ".config/probe.conf").exists())
        self.assertFalse((self.home / ".config/probe").exists())
        self.assertTrue((self.home / ".config/other.conf").exists())

    def shared_files(self):
        share = self.home / ".local/share/frame-tweaks"
        for d in ("i18n", "packs/mine"):
            (share / d).mkdir(parents=True, exist_ok=True)
        (self.home / ".cache/frame-tweaks").mkdir(parents=True, exist_ok=True)
        (self.home / ".config/frame-tweaks/installer").mkdir(parents=True, exist_ok=True)
        (self.home / ".config/frame-tweaks/language").write_text("es_419\n")
        (self.state / "backups/firefox").mkdir(parents=True)
        (self.state / "backups/firefox/user.js").write_text("as it was")
        (self.state / "logs").mkdir(parents=True, exist_ok=True)

    def test_uninstall_self_removes_every_tweak_and_what_they_shared(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.settings_made()
        self.shared_files()
        r = self.sh("uninstall-self", "--remove-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("uninstall", self.log())
        self.assertFalse((self.home / "probe-installed").exists())
        self.assertFalse((self.home / ".config/probe.conf").exists())              # its settings
        self.assertFalse((self.home / ".config/frame-tweaks").exists())            # Frame Tweaks' own
        self.assertTrue((self.home / ".config/other.conf").exists())
        self.assertFalse((self.home / ".local/share/frame-tweaks/i18n").exists())
        self.assertTrue((self.home / ".local/share/frame-tweaks/packs/mine").is_dir())   # your own packs
        self.assertFalse((self.home / ".cache/frame-tweaks").exists())
        self.assertEqual(sorted(p.name for p in self.state.iterdir()), ["backups"])     # not yet put back
        self.assertIn("FRAME_TWEAKS_KEEP_CHECKOUT: kept", r.stdout)
        self.assertIn("Frame Tweaks is uninstalled.", r.stdout)

    def test_uninstall_self_keeping_tweaks_and_settings(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.settings_made()
        self.shared_files()
        r = self.sh("uninstall-self", "--keep-tweaks", "--remove-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.home / "probe-installed").exists())
        self.assertTrue((self.home / ".config/probe.conf").exists())               # in use
        self.assertFalse((self.home / ".config/frame-tweaks/installer").exists())
        self.assertTrue((self.home / ".config/frame-tweaks/language").exists())    # (the tweaks follow it)
        self.assertTrue((self.home / ".local/share/frame-tweaks/i18n").is_dir())
        self.assertTrue(self.record.exists())
        self.assertIn("Kept for the tweaks still installed (probe)", r.stdout)
        self.trust()
        self.only_the_probe()          # (the settings just removed held them, and the trust)
        r = self.sh("uninstall-self", "--keep-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / "probe-installed").exists())
        self.assertTrue((self.home / ".config/probe.conf").exists())
        self.assertTrue((self.home / ".config/frame-tweaks/language").exists())
        self.assertIn("Kept the settings", r.stdout)

    def test_uninstall_self_counts_tweaks_of_packs_not_in_use(self):
        """A tweak from a pack turned off or no longer trusted isn't listed, but its install record
        is there: what it shares stays."""
        self.shared_files()
        (self.state / "installed").mkdir(parents=True, exist_ok=True)
        (self.state / "installed/set-aside").write_text("0.6.1\n")
        r = self.sh("uninstall-self", "--remove-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("from packs not in use (turned off, or not trusted): set-aside", r.stdout)
        self.assertTrue((self.home / ".local/share/frame-tweaks/i18n").is_dir())
        self.assertTrue((self.state / "installed/set-aside").exists())

    def test_uninstall_self_with_every_pack_off(self):
        (self.home / ".config/frame-tweaks/installer/trusted-packs").unlink()     # (the probe's pack too)
        self.shared_files()
        r = self.sh("uninstall-self", "--keep-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Frame Tweaks is uninstalled.", r.stdout)
        self.assertFalse((self.home / ".local/share/frame-tweaks/i18n").exists())

    def app_tweak(self):
        """A second tweak, "probeapp", that installs another project's app (manifest app:)."""
        d = self.pack / "probeapp"
        d.mkdir()
        (d / "README.md").write_text(README.replace("title: Probe", "title: Probe App").replace(
            "processes: []", "processes: []\napp: Probe App").replace("uninstall probe", "uninstall probeapp"))
        scripts = {k: v.replace("probe-installed", "probeapp-installed").replace("probe.log", "probeapp.log")
                   for k, v in SCRIPTS.items()}
        for name, body in scripts.items():
            (d / name).write_text(f"#!/bin/bash\n{body}\n")
        self.trust()
        self.assertEqual(self.sh("install", "probe", "probeapp").returncode, 0)

    def test_uninstall_self_leaves_other_projects_apps_by_default(self):
        self.app_tweak()
        r = self.sh("uninstall-self", "--keep-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / "probe-installed").exists())
        self.assertTrue((self.home / "probeapp-installed").exists())
        self.assertIn("Left installed, as asked: Probe App", r.stdout)
        self.assertIn("Kept for the tweaks still installed (probeapp)", r.stdout)     # (what it may use)
        r = self.sh("uninstall-self", "--remove-apps", "--keep-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / "probeapp-installed").exists())

    def test_frame_tweaks_installed_again_finds_the_tweaks_it_left(self):
        """Uninstalled with --keep-tweaks (and its own settings deleted), then installed again (here:
        the same checkout, as get.sh would make anew): the tweak shows as installed, at the version
        recorded, so updates and uninstalling work as before. A pack of your own needs trusting
        again: that was among the settings deleted. (Official packs need no trust.)"""
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.settings_made()
        self.shared_files()
        r = self.sh("uninstall-self", "--keep-tweaks", "--remove-settings")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / ".local/share/applications/io.github.AstronautCheetah.FrameTweaks.desktop").exists())
        # installed again
        self.assertNotIn("probe", self.sh("list").stdout)                    # (not trusted any more)
        self.trust()
        self.only_the_probe()
        self.assertEqual(self.sh("menu").returncode, 0)
        self.assertTrue((self.home / ".local/share/applications/io.github.AstronautCheetah.FrameTweaks.desktop").exists())
        r = self.sh("status", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("installed", r.stdout)
        self.assertEqual(self.record.read_text().strip(), VERSION)              # (no migration re-run)
        self.assertTrue((self.home / ".config/probe.conf").exists())             # (its settings: in use)
        r = self.sh("install", "probe")
        self.assertNotIn("migrate", " ".join(self.log()))
        r = self.sh("uninstall", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / "probe-installed").exists())

    def test_uninstall_self_stops_when_a_tweak_wont_go(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.shared_files()
        (self.pack / "probe/uninstall.sh").write_text("#!/bin/bash\nexit 1\n")
        self.trust()
        r = self.sh("uninstall-self")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Frame Tweaks is still here", r.stdout + r.stderr)         # (the log takes both)
        self.assertTrue((self.home / ".local/share/frame-tweaks/i18n").is_dir())
        self.assertTrue((self.home / ".config/frame-tweaks/installer").is_dir())

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

    def test_the_last_five_logs_are_kept_and_others_left_alone(self):
        logs = self.state / "logs"
        (logs / "mytweak").mkdir(parents=True)
        theirs = [logs / "links.log", logs / "mytweak/20250101-000000.log"]     # (a tweak's own, dated)
        ours = [logs / f"2026010{i}-000000-{i}-install.log" for i in range(1, 8)]
        for n, p in enumerate(theirs + ours):                # (oldest first)
            p.write_text("x\n")
            os.utime(p, (1767225600 + n, 1767225600 + n))
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        kept = sorted(p.name for p in logs.glob("[0-9]*-*.log"))
        self.assertEqual(kept[:-1], [p.name for p in ours[3:]])   # (the four newest, then this run's)
        for p in theirs:
            self.assertTrue(p.exists(), p)

    def test_install_all_migrates_too(self):
        self.only_the_probe()
        self.installed_at("0.0.1")
        r = self.sh("install", "all")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.log(), ["migrate 0.0.1", "install"])

    def test_a_failed_uninstall_is_reported_and_keeps_the_record(self):
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        (self.pack / "probe/uninstall.sh").write_text('#!/bin/bash\necho uninstall >> "$HOME/probe.log"; exit 1\n')
        self.trust()
        r = self.sh("uninstall", "probe")
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Failed: probe", r.stdout)                    # (the log has stderr too)
        self.assertEqual(self.log(), ["install", "uninstall"])
        self.assertEqual(self.record.read_text(), VERSION + "\n")     # (still installed)

    def test_debug_info_removes_names_and_addresses(self):
        """Here from a log of an earlier run, which the report includes."""
        self.only_the_probe()
        host, phone = "frame-bob", "Galaxy S24+ (Bob)"      # (+ and ( ) mean something to sed -E)
        self.stub("hostname", f"echo {host}")
        (self.home / ".config/frame-tweaks/phone.conf").write_text(f"PHONE_NAME={shlex.quote(phone)}\n")
        logs = self.state / "logs"
        logs.mkdir(parents=True)
        (logs / "20260101-000000-1-install.log").write_text(
            f"Connecting to {phone}…\nalice@{host}:{self.home}/x$ adb connect 192.168.1.23:37011\n"
            "bluetooth aa:bb:cc:dd:ee:0f, fe80::1c2b:3aff:fe4d:5e6f%wlan0, mail bob.smith@example.com\n")
        r = self.sh("debug-info", USER="alice")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        report = Path(re.search(r"^Wrote (.+)$", r.stdout, re.M)[1]).read_text()
        self.assertIn("Connecting to <phone>…", report)
        self.assertIn("<user>@<host>:~/x$ adb connect <ip>:37011", report)
        self.assertIn("bluetooth <mac>, <ipv6>%wlan0, mail <email>", report)
        for secret in (phone, host, str(self.home), "alice", "192.168", "example.com"):
            self.assertNotIn(secret, report)


LINKED = """\
---
title: Linked
emoji: 🔗
category: Tests
tier: extras
summary: A project that installs itself
what: Linked, not integrated.
why: For tests.
author: Tests
changes: Whatever its installer does
access: None
survives_updates: Its own concern
undo: ./install.sh uninstall linked
run: {label: Open}
link:
  install: echo installed >> ~/linked.log; mkdir -p ~/linked-project
  uninstall: echo uninstalled >> ~/linked.log; rm -rf ~/linked-project
  installed: [~/linked-project, ~/.local/share/linked-project]
  run: touch ~/linked-ran
  readme: https://example.org/linked#readme
---
# Linked
"""


class LinkedProject(unittest.TestCase):
    """A tweak with link: and no scripts: the project's own commands run (lib/link.sh), its status is
    whether a path exists, ↻ runs its installer again without uninstalling it first, and Frame
    Tweaks' updates leave it alone. (InstallState's home and probe pack, not its tests.)"""
    stub, trust, only_the_probe, sh, tearDown = (InstallState.stub, InstallState.trust, InstallState.only_the_probe,
                                                 InstallState.sh, InstallState.tearDown)

    def setUp(self):
        InstallState.setUp(self)
        (self.pack / "linked").mkdir()
        (self.pack / "linked/README.md").write_text(LINKED)
        self.trust()

    def linked_log(self):
        p = self.home / "linked.log"
        return p.read_text().split() if p.exists() else []

    def test_install_status_reinstall_and_uninstall(self):
        self.assertIn("not installed", self.sh("status", "linked").stdout)
        r = self.sh("install", "linked")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("with its own installer", r.stdout)
        self.assertEqual(self.linked_log(), ["installed"])
        r = self.sh("status", "linked")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("installed by its own installer", r.stdout)
        self.sh("reinstall", "linked")                                  # (↻: its installer again, no uninstall)
        self.assertEqual(self.linked_log(), ["installed", "installed"])
        r = self.sh("uninstall", "linked")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.linked_log(), ["installed", "installed", "uninstalled"])
        self.assertIn("not installed", self.sh("status", "linked").stdout)

    def test_updates_leave_it_alone(self):
        self.sh("install", "linked")
        r = self.sh("_reinstall", FRAME_TWEAKS_UPDATING="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Linked, so they update their own way", r.stdout)
        self.assertEqual(self.linked_log(), ["installed"])

    def test_restart_steamvr(self):
        """restart: steamvr: installed after SteamVR started, it isn't loaded yet; uninstalled after
        SteamVR started, SteamVR still runs it. Either way the row offers to restart SteamVR, until
        it has restarted. (pgrep and ps are stand-ins.)"""
        (self.pack / "linked/README.md").write_text(LINKED.replace("  readme:", "  restart: steamvr\n  readme:"))
        self.trust()
        self.sh("install", "linked")
        os.utime(self.home / "linked-project", (time.time() - 3600,) * 2)       # installed an hour ago
        self.stub("pgrep", '[ "$*" = "-xo vrserver" ] && echo 4242 || exit 1')
        for started, says in ((7200, "installed; restart SteamVR to load it"),
                              (60, "installed by its own installer")):
            self.stub("ps", f"echo {started}")
            self.assertIn(says, self.sh("status", "linked").stdout, started)
        self.assertIn("Restart SteamVR to unload it", self.sh("uninstall", "linked").stdout)
        os.utime(self.home / ".local/state/frame-tweaks/unloaded/linked", (time.time() - 3600,) * 2)
        for started, says, code in ((7200, "uninstalled; restart SteamVR to unload it", 1), (60, "not installed", 1)):
            self.stub("ps", f"echo {started}")
            self.assertIn(says, self.sh("status", "linked").stdout, started)
            r = subprocess.run(["bash", str(ROOT / "lib/link.sh"), "status", "linked"], env=self.env,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, code, r.stdout)          # (not installed, either way)
        self.sh("install", "linked")                                    # (installing again forgets it)
        self.assertFalse((self.home / ".local/state/frame-tweaks/unloaded/linked").exists())

    def test_vrmonitor_links_go_nowhere(self):
        """SteamVR's vrpathreg runs xdg-open vrmonitor://driverinstalled as a driver is registered;
        nothing on the Frame opens it, so a linked installer's call does nothing. Other links open."""
        self.stub("xdg-open", 'echo "$1" >> ~/opened')
        (self.pack / "linked/README.md").write_text(LINKED.replace(
            "install: echo installed", "install: xdg-open vrmonitor://driverinstalled; xdg-open https://example.org; echo installed"))
        self.trust()
        r = self.sh("install", "linked")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.home / "opened").read_text().split(), ["https://example.org"])

    def test_run(self):
        self.sh("install", "linked")
        self.assertEqual(self.sh("run", "linked").returncode, 0)
        for _ in range(50):                                             # (started in the background)
            if (self.home / "linked-ran").exists():
                break
            time.sleep(0.1)
        self.assertTrue((self.home / "linked-ran").exists())


if __name__ == "__main__":
    unittest.main()
