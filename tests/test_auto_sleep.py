"""Sleep when idle in VR (packs/bugfixes/auto-sleep): when it puts the Frame to sleep, reading SteamVR's standby
lines, its settings, and its status line. Background: docs/research/idle-sleep.md. Run: python3 -m unittest -v"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script, sandbox_env  # noqa: E402

TWEAK = ROOT / "packs/bugfixes/auto-sleep"
sleep = load_script(TWEAK / "frame-tweaks-auto-sleep")
CONF = dict(sleep.DEFAULTS)
NOW = 1_800_000_000.0


class Decide(unittest.TestCase):
    def test_sleeps_after_the_wait_on_battery(self):
        self.assertEqual(sleep.decide(NOW, NOW - 15 * 60, True, CONF)[0], 0)
        left, why = sleep.decide(NOW, NOW - 5 * 60, True, CONF)
        self.assertEqual(left, 600)
        self.assertIn("on battery", why)

    def test_plugged_in_waits_longer(self):
        self.assertEqual(sleep.decide(NOW, NOW - 15 * 60, False, CONF)[0], 45 * 60)

    def test_never_while_worn_or_without_steamvr(self):
        self.assertIsNone(sleep.decide(NOW, None, True, CONF)[0])
        self.assertIsNone(sleep.decide(NOW, NOW - 3600, True, CONF, vr_running=False)[0])

    def test_off_is_off(self):
        self.assertIsNone(sleep.decide(NOW, NOW - 3600, True, dict(CONF, AUTO_SLEEP_BATTERY="0"))[0])
        self.assertIsNone(sleep.decide(NOW, NOW - 3600, True, dict(CONF, AUTO_SLEEP_BATTERY="soon"))[0])

    def test_someone_over_ssh_keeps_it_awake_unless_allowed(self):
        left, why = sleep.decide(NOW, NOW - 3600, True, CONF, remote=["steamos"])
        self.assertIsNone(left)
        self.assertIn("SSH", why)
        self.assertEqual(sleep.decide(NOW, NOW - 3600, True, dict(CONF, AUTO_SLEEP_SSH="yes"), remote=["s"])[0], 0)

    def test_a_block_on_sleep_is_respected(self):
        self.assertIsNone(sleep.decide(NOW, NOW - 3600, True, CONF, blockers=["backup"])[0])

    def test_the_wait_starts_again_after_a_wake(self):
        self.assertEqual(sleep.decide(NOW, NOW - 3600, True, CONF, resumed=NOW - 60)[0], 14 * 60)


class Standby(unittest.TestCase):
    def log(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
        f.write(text)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_the_headsets_last_word(self):
        path = self.log("Wed Nov 18 2026 20:36:41.887527 [Info] - 0 - entering standby\n"
                        "Wed Nov 18 2026 20:36:41.900000 [Info] - cv:  [CCVTrackedHmdDriver] in StateStandby \n"
                        "Wed Nov 18 2026 20:42:51.915181 [Info] - 1 - entering standby\n")
        t = sleep.standby_since(path)
        self.assertEqual(time.localtime(t)[:6], (2026, 11, 18, 20, 36, 41))

    def test_in_use_after_leaving(self):
        path = self.log("Wed Nov 18 2026 20:36:41.887527 [Info] - 0 - entering standby\n"
                        "Wed Nov 18 2026 20:40:00.000000 [Info] - 0 - leaving standby\n"
                        "Wed Nov 18 2026 20:41:00.000000 [Info] - 2 - entering standby\n")
        self.assertIsNone(sleep.standby_since(path))

    def test_no_word_or_no_log(self):
        self.assertIsNone(sleep.standby_since(self.log("nothing about standby\n")))
        self.assertIsNone(sleep.standby_since("/nonexistent/vrserver.txt"))


class Settings(unittest.TestCase):
    def test_reads_its_keys_and_keeps_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "auto-sleep.conf")
            with open(p, "w") as f:
                f.write("AUTO_SLEEP_BATTERY='5'\nOTHER=x\n# AUTO_SLEEP_PLUGGED=1\n")
            got = sleep.settings(p)
        self.assertEqual(got, dict(sleep.DEFAULTS, AUTO_SLEEP_BATTERY="5"))
        self.assertEqual(sleep.settings("/nonexistent"), sleep.DEFAULTS)

    def test_the_readme_offers_what_the_service_reads(self):
        text = (TWEAK / "README.md").read_text()
        for key, default in sleep.DEFAULTS.items():
            self.assertIn(f"key: {key}", text)
            self.assertIn(f'default: "{default}"', text)


class OnBattery(unittest.TestCase):
    def test_the_charger_service_says(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ac_status")
            for value, battery in (("Connected", False), ("Disconnected", True)):
                Path(p).write_text(value + "\n")
                self.assertIs(sleep.on_battery(p), battery)


class StatusLine(unittest.TestCase):
    def test_over_ssh_it_also_says_when_it_would_sleep(self):
        from unittest import mock
        with mock.patch.object(sleep, "standby_since", return_value=time.time() - 5 * 60), \
                mock.patch.object(sleep, "on_battery", return_value=True), \
                mock.patch.object(sleep, "vrserver_running", return_value=True), \
                mock.patch.object(sleep, "remote_sessions", return_value=["steamos"]), \
                mock.patch.object(sleep, "sleep_blockers", return_value=[]), \
                mock.patch.object(sleep, "settings", return_value=dict(CONF)), \
                mock.patch("sys.stdout", new_callable=__import__("io").StringIO) as out:
            sleep.status()
        self.assertEqual(out.getvalue().strip(), "not now: steamos logged in over SSH; otherwise in 10 min")


class Status(unittest.TestCase):
    def test_not_installed(self):
        with tempfile.TemporaryDirectory() as home:
            r = subprocess.run(["bash", str(TWEAK / "status.sh")], env=sandbox_env(home), capture_output=True,
                               text=True)
        self.assertIn("not installed", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
