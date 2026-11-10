"""Why a tweak's script runs, and repairing after a SteamOS update. In test_install_state.py's
throwaway home with its trusted probe pack: install.sh, uninstall.sh and migrate.sh get FT_PHASE,
FT_REASON and FT_PREVIOUS_VERSION for every phase (FRAME_TWEAKS_REINSTALL as before);
./install.sh repair installs again only what's broken (missing with a record, or a warning) and
doesn't say it survives SteamOS updates, leaves held tweaks and those not installed alone, and
records the SteamOS build (FRAME_TWEAKS_OS_RELEASE stands in for /etc/os-release); and the build
change the window offers Repair for (lib/sft.py build_change, broken)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_install_state import README, SCRIPTS, VERSION, InstallState  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import sft  # noqa: E402

# (every script logs why it runs: phase, reason, <previous version>, and FRAME_TWEAKS_REINSTALL)
CONTEXT = 'echo "{word} $FT_PHASE $FT_REASON <$FT_PREVIOUS_VERSION> r=${{FRAME_TWEAKS_REINSTALL:-}}" >> "$HOME/context.log"'
FRAGILE = {
    "install.sh": 'echo "install $FT_PHASE $FT_REASON" >> "$HOME/fragile.log"; touch "$HOME/fragile-installed"; '
                  'rm -f "$HOME/fragile-broken"',
    "uninstall.sh": 'echo uninstall >> "$HOME/fragile.log"; rm -f "$HOME/fragile-installed"',
    "status.sh": '[ -f "$HOME/fragile-broken" ] && { echo "warning  its rule is gone"; exit 2; }\n'
                 '[ -f "$HOME/fragile-installed" ] && { echo "ok       installed"; exit 0; }; echo "missing  no"; exit 1',
}


def os_release(path, build):
    path.write_text(f'NAME="SteamOS"\nID=steamos\nVERSION_ID=3.8.0\nBUILD_ID={build}\n')


class Lifecycle(unittest.TestCase):
    stub, trust, only_the_probe, sh, tearDown, installed_at = (
        InstallState.stub, InstallState.trust, InstallState.only_the_probe, InstallState.sh, InstallState.tearDown,
        InstallState.installed_at)

    def setUp(self):
        InstallState.setUp(self)
        for name in ("install.sh", "uninstall.sh", "migrate.sh"):
            (self.pack / "probe" / name).write_text(f"#!/bin/bash\n{SCRIPTS[name]}\n{CONTEXT.format(word=name[:-3])}\n")
        self.trust()
        self.osr = Path(self.tmp.name) / "os-release"
        os_release(self.osr, "20261001.1")
        self.env["FRAME_TWEAKS_OS_RELEASE"] = str(self.osr)

    def context(self):
        """What the scripts logged since the last call."""
        p = self.home / "context.log"
        lines = p.read_text().splitlines() if p.exists() else []
        p.unlink(missing_ok=True)
        return lines

    def ok(self, *args, **extra):
        r = self.sh(*args, **extra)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def test_every_phase(self):
        self.ok("install", "probe")
        self.assertEqual(self.context(), ["install install user <> r="])
        self.ok("install", "probe")
        self.assertEqual(self.context(), [f"install install user <{VERSION}> r="])
        # (↻: its uninstall first, with FRAME_TWEAKS_REINSTALL as before; the install still knows
        # the version, though the record went between the two)
        self.ok("reinstall", "probe")
        self.assertEqual(self.context(), [f"uninstall reinstall user <{VERSION}> r=1",
                                          f"install reinstall user <{VERSION}> r="])
        (self.pack / "probe/notes.txt").write_text("changed\n")      # (its files changed: reinstall-changed)
        self.trust()
        self.ok("reinstall-changed")
        self.assertEqual(self.context(), [f"install reinstall reinstall-changed <{VERSION}> r="])
        self.installed_at("0.0.1")
        self.ok("_reinstall", FRAME_TWEAKS_UPDATING="1")
        self.assertEqual(self.context(), ["migrate update update <0.0.1> r=", "install update update <0.0.1> r="])
        (self.home / "probe-installed").unlink()                     # (what a SteamOS update did to it)
        (self.pack / "probe/README.md").write_text(README.replace('survives_updates: "Yes"', 'survives_updates: "No"'))
        self.trust()
        self.ok("repair")
        self.assertEqual(self.context(), [f"install repair repair <{VERSION}> r="])
        (self.home / "probe-installed").unlink()
        self.ok("repair", "--steamos-update")
        self.assertEqual(self.context(), [f"install repair steamos-update <{VERSION}> r="])
        self.ok("uninstall", "probe")
        self.assertEqual(self.context(), [f"uninstall uninstall user <{VERSION}> r="])

    def test_status_checks_dont_get_it(self):
        """Only the scripts that change something: a status.sh run during an install doesn't."""
        (self.pack / "probe/status.sh").write_text('#!/bin/bash\necho "status ${FT_PHASE:-none}" >> "$HOME/context.log"\n'
                                                   + SCRIPTS["status.sh"] + "\n")
        self.trust()
        self.ok("install", "probe")
        self.assertIn("status none", self.context())


class Repair(unittest.TestCase):
    stub, trust, only_the_probe, sh, tearDown = (InstallState.stub, InstallState.trust, InstallState.only_the_probe,
                                                 InstallState.sh, InstallState.tearDown)

    def setUp(self):
        InstallState.setUp(self)
        d = self.pack / "fragile"
        d.mkdir()
        (d / "README.md").write_text(README.replace("title: Probe", "title: Fragile")
                                     .replace('survives_updates: "Yes"', 'survives_updates: "No, an update removes its rule"')
                                     .replace("uninstall probe", "uninstall fragile")
                                     .replace("config: [~/.config/probe.conf, ~/.config/probe]\n", ""))
        for name, body in FRAGILE.items():
            (d / name).write_text(f"#!/bin/bash\n{body}\n")
        self.trust()
        self.osr = Path(self.tmp.name) / "os-release"
        os_release(self.osr, "20261001.1")
        self.env["FRAME_TWEAKS_OS_RELEASE"] = str(self.osr)
        self.build = self.state / "steamos-build"

    def fragile_log(self):
        p = self.home / "fragile.log"
        return p.read_text().splitlines() if p.exists() else []

    def probe_log(self):
        p = self.home / "probe.log"
        return p.read_text().splitlines() if p.exists() else []

    def test_after_a_steamos_update(self):
        """Both missing though installed: the one that doesn't say it survives updates is installed
        again (not removed first); the one that says Yes is named as still broken, with how to
        reinstall it anyway. The new build is recorded."""
        r = self.sh("install", "probe", "fragile")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.build.read_text(), "3.8.0 (20261001.1)\n")
        os_release(self.osr, "20261020.1")
        (self.home / "probe-installed").unlink()
        (self.home / "fragile-installed").unlink()
        r = self.sh("repair")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)         # (probe is still broken)
        self.assertEqual(self.fragile_log(), ["install install user", "install repair repair"])
        self.assertEqual(self.probe_log(), ["install"])
        self.assertIn("Repaired: fragile", r.stdout)
        self.assertRegex(r.stdout, r"probe +its manifest says it survives SteamOS updates.*\./install\.sh reinstall probe")
        self.assertIn("Still broken: probe", r.stdout)
        self.assertEqual(self.build.read_text(), "3.8.0 (20261020.1)\n")

    def test_a_warning_counts_and_working_ones_are_left(self):
        self.assertEqual(self.sh("install", "probe", "fragile").returncode, 0)
        (self.home / "fragile-broken").touch()
        r = self.sh("repair", "--steamos-update")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.fragile_log(), ["install install user", "install repair steamos-update"])
        self.assertEqual(self.probe_log(), ["install"])                  # (working: not run)
        self.assertIn("Repaired: fragile", r.stdout)
        self.assertNotIn("Still broken", r.stdout)
        r = self.sh("repair")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Nothing to repair", r.stdout)
        self.assertEqual(len(self.fragile_log()), 2)

    def test_not_installed_and_held_tweaks_are_left_alone(self):
        """Missing without a record is just not installed; a held tweak stays as it is, and says so."""
        r = self.sh("repair")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Nothing to repair", r.stdout)
        self.assertEqual(self.fragile_log(), [])
        self.assertEqual(self.sh("install", "fragile").returncode, 0)
        self.assertEqual(self.sh("hold", "fragile").returncode, 0)
        (self.home / "fragile-installed").unlink()
        r = self.sh("repair")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.fragile_log(), ["install install user"])
        self.assertIn("held: left as it is (./install.sh unhold fragile)", r.stdout)

    def test_a_repair_that_doesnt_fix_it_says_so(self):
        self.assertEqual(self.sh("install", "fragile").returncode, 0)
        (self.pack / "fragile/install.sh").write_text('#!/bin/bash\necho "install $FT_PHASE" >> "$HOME/fragile.log"\n')
        self.trust()
        (self.home / "fragile-installed").unlink()
        r = self.sh("repair")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.fragile_log(), ["install install user", "install repair"])
        self.assertRegex(r.stdout, r"fragile +still broken after installing it again: no")
        self.assertIn("Still broken: fragile", r.stdout)

    def test_the_build_is_recorded_at_the_first_install_and_each_repair(self):
        """Not at every install: one new tweak installed right after a SteamOS update would hide the
        window's Repair offer while the others are still broken."""
        self.assertEqual(self.sh("install", "probe").returncode, 0)
        self.assertEqual(self.build.read_text(), "3.8.0 (20261001.1)\n")
        # (each install record names the build it was made on, after the Frame Tweaks version)
        self.assertEqual((self.state / "installed/probe").read_text().splitlines()[1], "3.8.0 (20261001.1)")
        os_release(self.osr, "20261020.1")
        self.assertEqual(self.sh("install", "fragile").returncode, 0)
        self.assertEqual(self.build.read_text(), "3.8.0 (20261001.1)\n")
        self.assertEqual((self.state / "installed/fragile").read_text().splitlines()[1], "3.8.0 (20261020.1)")
        self.assertEqual(self.sh("repair").returncode, 0)
        self.assertEqual(self.build.read_text(), "3.8.0 (20261020.1)\n")
        self.build.unlink()
        self.osr.unlink()                                                # (can't tell: nothing recorded)
        self.assertEqual(self.sh("repair").returncode, 0)
        self.assertFalse(self.build.exists())

    def test_an_unknown_option_is_refused(self):
        r = self.sh("repair", "fragile")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("repair: unknown option fragile", r.stdout + r.stderr)      # (through the log's tee)
        self.assertEqual(self.fragile_log(), [])


class BuildChange(unittest.TestCase):
    """lib/sft.py: the SteamOS build, read from os-release, compared with the recorded one; what the
    window counts as broken; what says it survives updates."""
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.osr = self.dir / "os-release"
        for p in (mock.patch.object(sft, "STATE", self.dir / "state"),
                  mock.patch.dict(os.environ, {"FRAME_TWEAKS_OS_RELEASE": str(self.osr)})):
            p.start()
            self.addCleanup(p.stop)

    def test_reading_os_release(self):
        self.assertEqual(sft.steamos_build('VERSION_ID=3.8.0\nBUILD_ID="20261020.1"\n'), "3.8.0 (20261020.1)")
        self.assertEqual(sft.steamos_build("NAME=x\nVERSION_ID='3.7'\n"), "3.7")
        self.assertEqual(sft.steamos_build("BUILD_ID=20261020.1\n"), "20261020.1")
        self.assertEqual(sft.steamos_build("NAME=x\n"), "")
        self.assertEqual(sft.steamos_build(), "")                       # (no such file)

    def test_a_change_needs_a_record_and_a_build(self):
        self.assertIsNone(sft.build_change())                           # (neither)
        os_release(self.osr, "1")
        self.assertIsNone(sft.build_change())                           # (no record: nothing to compare)
        self.assertEqual(sft.record_build(), "3.8.0 (1)")
        self.assertIsNone(sft.build_change())
        self.assertEqual(sft.record_build(only_if_missing=True), "3.8.0 (1)")
        os_release(self.osr, "2")
        self.assertEqual(sft.build_change(), ("3.8.0 (1)", "3.8.0 (2)"))
        sft.record_build(only_if_missing=True)                          # (a record there: kept)
        self.assertEqual(sft.build_change(), ("3.8.0 (1)", "3.8.0 (2)"))
        self.osr.unlink()
        self.assertIsNone(sft.build_change())                           # (can't tell now)

    def test_broken(self):
        self.assertTrue(sft.broken((2, "warning"), False))
        self.assertTrue(sft.broken((1, "missing"), True))               # (installed, then gone)
        self.assertFalse(sft.broken((1, "missing"), False))             # (never installed)
        self.assertFalse(sft.broken((0, "ok"), True))
        self.assertFalse(sft.broken((sft.installer.RESTART, "load it"), True))   # (a SteamVR restart's to fix)
        self.assertFalse(sft.broken(None, True))                        # (not checked yet)

    def test_installed_on_this_build(self):
        """The record's second line is the build the tweak was installed on: equal to the one running
        now, the tweak was installed after the update, so its warning isn't the update's doing."""
        rec = self.dir / "state/installed"
        rec.mkdir(parents=True)
        os_release(self.osr, "2")
        self.assertFalse(sft.installed_on_this_build("probe"))               # (no record)
        (rec / "probe").write_text("0.7.4\n")
        self.assertFalse(sft.installed_on_this_build("probe"))               # (an old record: no build)
        (rec / "probe").write_text("0.7.5\n3.8.0 (1)\n")
        self.assertFalse(sft.installed_on_this_build("probe"))               # (installed on the old build)
        (rec / "probe").write_text("0.7.5\n3.8.0 (2)\n")
        self.assertTrue(sft.installed_on_this_build("probe"))
        self.osr.unlink()
        self.assertFalse(sft.installed_on_this_build("probe"))               # (can't tell the build: says nothing)

    def test_survives_updates(self):
        for text, want in (("Yes (everything is in your home folder)", True), ("yes; it checks", True),
                           ("No, an update removes its rule", False), ("Yesterday's rule", False),
                           ("Its own concern", False), ("", False), (None, False)):
            self.assertEqual(sft.survives_updates({"survives_updates": text}), want, text)
        # (the official packs say Yes, as they should, each one)
        self.assertTrue(all(sft.survives_updates(c) for c in sft.components() if c["id"] in ("arrowpad", "tools")))


if __name__ == "__main__":
    unittest.main()
