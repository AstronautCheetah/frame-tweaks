"""Battery charge limit (packs/original/charge-limit): charge-limit pauses the charger at the limit
and lets it charge again 5% below, lifts only its own pause, follows the setting and Charge to
100% once, and lets the battery charge when it stops; its status says how it's holding, and when
SteamOS has a charge limit of its own for the Frame. A folder laid out like /sys stands in for the
battery and the charger."""
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TWEAK = ROOT / "packs/original/charge-limit"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402


class ChargeLimit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        ps = self.home / "sys/power_supply"
        self.bat, charger = ps / "max1720x_bat_7-36", ps / "pm8550b-charger"
        for d in (self.bat, charger):
            d.mkdir(parents=True)
        (self.bat / "type").write_text("Battery\n")
        (charger / "type").write_text("Unknown\n")
        self.switch = charger / "charging_pause"
        self.switch.write_text("0\n")
        self.conf = self.home / ".config/frame-tweaks/charge-limit.conf"
        self.conf.parent.mkdir(parents=True)
        self.run_dir = self.home / "run/charge-limit"
        self.stubs = self.home / "stubs"
        self.env = sandbox_env(self.home, self.stubs, FRAME_TWEAKS_POWER_SUPPLY=ps,
                               FRAME_TWEAKS_BATTERY=self.home / "no-BAT0", FRAME_TWEAKS_CHARGE_RUN=self.run_dir,
                               FRAME_TWEAKS_CHARGE_INTERVAL="0.2")
        self.battery(70)

    def battery(self, capacity, status="Charging", current=1300000):
        (self.bat / "capacity").write_text(f"{capacity}\n")
        (self.bat / "status").write_text(status + "\n")
        (self.bat / "current_now").write_text(f"{current}\n")

    def limit(self, value):
        self.conf.write_text(f'CHARGE_LIMIT="{value}"\n')

    def cl(self, *args):
        r = subprocess.run(["bash", str(TWEAK / "charge-limit"), *args], env=self.env,
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def paused(self):
        return self.switch.read_text().strip() == "1"

    def test_pauses_at_the_limit_and_resumes_five_below(self):
        for capacity, paused in ((79, False), (80, True), (81, True), (77, True), (76, True), (75, False), (78, False)):
            self.battery(capacity)
            self.cl("--once")
            self.assertEqual(self.paused(), paused, capacity)

    def test_the_setting(self):
        self.assertEqual(self.cl("--limit"), "80\n")                   # (no settings yet: 80)
        for value, means in (("90", "90"), ("off", "off"), ("7", "80"), ("x; rm -rf ~", "80"), ("100", "100")):
            self.limit(value)
            self.assertEqual(self.cl("--limit"), means + "\n", value)
        self.limit("90")
        self.battery(85)
        self.cl("--once")
        self.assertFalse(self.paused())

    def test_turned_off_it_lifts_its_own_pause_only(self):
        self.battery(85)
        self.cl("--once")
        self.assertTrue(self.paused())
        self.limit("off")
        self.cl("--once")
        self.assertFalse(self.paused())
        self.switch.write_text("1\n")                                   # (someone else's pause)
        self.cl("--once")
        self.assertTrue(self.paused())

    def test_paused_again_after_steamos_clears_it(self):
        """SteamOS's charger service sets the switch to 0 as it starts."""
        self.battery(90)
        self.cl("--once")
        self.switch.write_text("0\n")
        self.cl("--once")
        self.assertTrue(self.paused())

    def test_charge_to_full_once(self):
        self.battery(85)
        self.cl("--once")
        self.cl("--full-once")
        self.assertFalse(self.paused())
        self.battery(95)
        self.cl("--once")
        self.assertFalse(self.paused())
        self.battery(100, "Full")
        self.cl("--once")                                               # full: the limit again
        self.assertFalse((self.run_dir / "full-once").exists())
        self.cl("--once")
        self.assertTrue(self.paused())

    def test_stopping_lets_it_charge(self):
        self.battery(90)
        p = subprocess.Popen(["bash", str(TWEAK / "charge-limit"), "--run"], env=self.env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(50):
                if self.paused():
                    break
                time.sleep(0.1)
            self.assertTrue(self.paused())
            p.send_signal(signal.SIGTERM)
            out, _ = p.communicate(timeout=10)
        finally:
            p.kill()
            p.communicate()
        self.assertFalse(self.paused())
        self.assertIn("charging paused at 90% (limit 80%)", out)

    def test_charge_to_full_once_button(self):
        """Its settings page's button (full-once.sh): only once installed, and nothing to do while
        the limit is off."""
        def press():
            return subprocess.run(["bash", str(TWEAK / "full-once.sh")], env=self.env, capture_output=True,
                                  text=True, timeout=30)
        r = press()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Install Battery charge limit first", r.stderr)
        bin_dir = self.home / ".local/bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "charge-limit").write_text((TWEAK / "charge-limit").read_text())
        (bin_dir / "charge-limit").chmod(0o755)
        self.limit("off")
        self.assertIn("already charges to 100%", press().stdout)
        self.assertFalse((self.run_dir / "full-once").exists())
        self.limit("80")
        self.battery(85)
        self.cl("--once")
        r = press()
        self.assertEqual(r.stdout, "Charging to 100% once; then the limit applies again.\n", r.stderr)
        self.assertTrue((self.run_dir / "full-once").exists())
        self.assertFalse(self.paused())

    # ---- status.sh --------------------------------------------------------------------------
    def status(self, devices="", active=True):
        stub(self.stubs, "systemctl", "exit 0" if active else "exit 3")
        bin_dir = self.home / ".local/bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / "charge-limit").write_text((TWEAK / "charge-limit").read_text())
        (bin_dir / "charge-limit").chmod(0o755)
        unit = self.home / ".config/systemd/user/charge-limit.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.touch()
        d = self.home / "steamos-manager"
        d.mkdir(exist_ok=True)
        (d / "steam-frame.toml").write_text('[[device]]\ndevice = "steam_frame"\n' + devices)
        r = subprocess.run(["bash", str(TWEAK / "status.sh")], capture_output=True, text=True, timeout=30,
                           env={**self.env, "FRAME_TWEAKS_CHARGE_SWITCH": str(self.switch),
                                "FRAME_TWEAKS_STEAMOS_DEVICES": str(d)})
        return r.returncode, r.stdout.strip()

    def test_status(self):
        self.assertEqual(self.status(), (0, "ok       Stops charging at 80% (battery 70%)"))
        self.battery(82, current=0)
        self.cl("--once")
        self.assertEqual(self.status(), (0, "ok       Holding at 80% (battery 82%, not charging)"))
        self.battery(82, current=900000)                                # (the charger ignored the pause)
        self.assertEqual(self.status()[0], 2)
        self.assertIn("still charges", self.status()[1])
        self.assertIn("Not running", self.status(active=False)[1])
        self.battery(85, current=0)
        self.switch.write_text("0\n")                                   # (at the limit, but not paused)
        code, text = self.status()
        self.assertEqual(code, 2)
        self.assertIn("charging isn't paused", text)
        self.limit("off")
        self.assertEqual(self.status(), (0, "ok       Limit off: charges to 100% (now 85%)"))

    def test_status_says_when_steamos_has_its_own(self):
        code, text = self.status("[battery_charge_limit]\nsuggested_minimum_limit = 10\n")
        self.assertEqual(code, 2)
        self.assertIn("SteamOS now has its own charge limit", text)


if __name__ == "__main__":
    unittest.main()
