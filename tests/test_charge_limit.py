"""Battery charge limit (packs/core/charge-limit): charge-limit pauses the charger at the limit
and lets it charge again 1% below, lifts only its own pause, follows the setting and Charge to
100% once, and lets the battery charge when it stops; its status says how it's holding, and when
SteamOS has a charge limit of its own for the Frame. A folder laid out like /sys stands in for the
battery and the charger."""
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TWEAK = ROOT / "packs/core/charge-limit"
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

    def test_pauses_at_the_limit_and_resumes_one_below(self):
        for capacity, paused in ((78, False), (79, False), (80, True), (81, True), (80, True), (79, False), (80, True)):
            self.battery(capacity)
            self.cl("--once")
            self.assertEqual(self.paused(), paused, capacity)

    def test_the_setting(self):
        self.assertEqual(self.cl("--limit"), "80\n")                   # (no settings yet: 80)
        for value, means in (("90", "90"), ("74", "74"), ("76", "76"), ("78", "78"), ("off", "off"), ("7", "80"),
                             ("x; rm -rf ~", "80"), ("100", "100")):
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

    def test_paused_before_sleep_near_the_limit(self):
        """Asleep, nothing checks the battery: going to sleep within SLEEP_WITHIN (10%) of the
        limit, or over it, charging pauses (and is ours to lift once awake); lower, it charges on
        so the Frame isn't left low; nor with the limit off or while charging to 100% once."""
        self.limit("78")
        for capacity, paused in ((77, True), (68, True), (90, True), (67, False), (40, False)):
            with self.subTest(capacity=capacity):
                self.switch.write_text("0\n")
                self.battery(capacity)
                out = self.cl("--before-sleep")
                self.assertEqual(self.paused(), paused)
                if paused:
                    self.assertIn(f"charging paused for sleep at {capacity}% (limit 78%)", out)
                    self.assertTrue((self.run_dir / "paused").exists())
        self.switch.write_text("0\n")
        self.battery(77)
        self.cl("--before-sleep")
        self.battery(76)                                                  # awake, a little lower
        self.cl("--after-sleep")
        self.assertFalse(self.paused())                                   # its own pause: lifted
        self.limit("off")
        self.switch.write_text("0\n")
        self.cl("--before-sleep")
        self.assertFalse(self.paused())
        self.limit("78")
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "full-once").touch()
        self.cl("--before-sleep")
        self.assertFalse(self.paused())

    def test_a_check_just_before_sleep_keeps_the_pause(self):
        """logind waits a few seconds for the other sleep locks after --before-sleep: the 30 s
        check landing then lifted the pause below the limit (77% of 78%), and the Frame charged to
        100% overnight. It stays until --after-sleep; a hold left by a missed wake lasts 10 minutes."""
        self.limit("78")
        self.battery(77)
        self.cl("--before-sleep")
        self.assertTrue(self.paused())
        self.cl("--once")                                                 # the check, before it sleeps
        self.assertTrue(self.paused())
        self.cl("--after-sleep")                                          # awake
        self.assertFalse(self.paused())
        self.cl("--before-sleep")
        hold = self.run_dir / "sleep-hold"
        old = time.time() - 11 * 60
        import os
        os.utime(hold, (old, old))
        self.cl("--once")
        self.assertFalse(self.paused())

    def test_the_service_starts_the_sleep_watch(self):
        """charge-limit --run starts charge-limit-sleep with its own path, and stops it too."""
        log = self.home / "sleeper.log"
        sleeper = self.home / "bin/charge-limit-sleep"
        stub(sleeper.parent, "charge-limit-sleep", f'echo "started $1" >> {log}; trap "echo stopped >> {log}; exit 0" TERM; '
                                                    'while :; do sleep 0.1; done')
        p = subprocess.Popen(["bash", str(TWEAK / "charge-limit"), "--run"], text=True,
                             env={**self.env, "FRAME_TWEAKS_CHARGE_SLEEPER": str(sleeper)},
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for _ in range(50):
                if log.exists():
                    break
                time.sleep(0.1)
            p.send_signal(signal.SIGTERM)
            p.communicate(timeout=10)
        finally:
            p.kill()
            p.communicate()
        for _ in range(30):
            if "stopped" in log.read_text():
                break
            time.sleep(0.1)
        self.assertEqual(log.read_text().split("\n")[:2], [f"started {TWEAK / 'charge-limit'}", "stopped"])

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
        self.switch.write_text("1\n")                                   # well over it (charged asleep)
        self.battery(98, current=0)
        self.assertEqual(self.status(), (0, "ok       Not charging until the battery is below 80% (now 98%)"))
        self.limit("off")
        self.assertEqual(self.status(), (0, "ok       Limit off: charges to 100% (now 98%)"))

    def test_status_says_when_the_sleep_watch_isnt_running(self):
        sleeper = self.home / ".local/bin/charge-limit-sleep"
        sleeper.parent.mkdir(parents=True, exist_ok=True)
        sleeper.write_text("#!/bin/sh\n")
        sleeper.chmod(0o755)
        stub(self.stubs, "pgrep", "exit 1")
        code, text = self.status()
        self.assertEqual(code, 2)
        self.assertIn("Not watching for sleep", text)
        stub(self.stubs, "pgrep", "echo 42")
        self.assertEqual(self.status(), (0, "ok       Stops charging at 80% (battery 70%)"))

    def test_status_says_when_steamos_has_its_own(self):
        code, text = self.status("[battery_charge_limit]\nsuggested_minimum_limit = 10\n")
        self.assertEqual(code, 2)
        self.assertIn("SteamOS now has its own charge limit", text)

    def test_status_while_charging_to_full_once(self):
        """Until the battery is full it says so, and the limit it goes back to; with the limit
        then turned off, that it's off (it said "then stopping at off% again")."""
        self.run_dir.mkdir(parents=True)
        (self.run_dir / "full-once").touch()
        self.battery(85)
        self.assertEqual(self.status(), (0, "ok       Charging to 100% once (now 85%), then stopping at 80% again"))
        self.limit("off")
        self.assertEqual(self.status(), (0, "ok       Limit off: charges to 100% (now 85%)"))

    # ---- uninstall.sh -----------------------------------------------------------------------
    def test_uninstall_finishes_without_the_switch(self):
        """The charger's pause switch gone (a SteamOS that renamed it, say): handing it back to
        root fails, and that ended the uninstall (set -e) right after its udev rule went. (A copy
        of uninstall.sh whose system paths are in the throwaway home; sudo is a stand-in.)"""
        etc = self.home / "etc"
        etc.mkdir()
        rule, keep = etc / "rule", etc / "keep"
        rule.write_text("rule\n")
        keep.write_text(f"{rule}\n")
        src = (TWEAK / "uninstall.sh").read_text()
        for old, new in (("/sys/class/power_supply/pm8550b-charger/charging_pause", self.home / "sys/gone/charging_pause"),
                         ("/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules", rule),
                         ("/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf", keep),
                         ("$XDG_RUNTIME_DIR_USER/charge-limit/paused", self.run_dir / "paused")):
            self.assertEqual(src.count(old), 1, old)              # (never the real ones)
            src = src.replace(old, str(new))
        script = self.home / "uninstall.sh"
        script.write_text(src)
        log = self.home / "sudo.log"
        # sudo: removes files only in this home; chown fails on a file that isn't there, as it does
        stub(self.stubs, "sudo", f'echo "sudo $*" >> {log}\ncase "$1" in -v) exit 0 ;;\n'
                                 f'  rm) shift; for f in "$@"; do case "$f" in -f) ;; "{self.home}"/*) rm -f "$f" ;; *) exit 1 ;; esac; done ;;\n'
                                 '  chown) [ -e "$3" ] || { echo "chown: cannot access $3" >&2; exit 1; } ;;\n  *) exit 1 ;; esac')
        stub(self.stubs, "systemctl", "exit 0")
        r = subprocess.run(["bash", str(script)], env={**self.env, "FRAME_TWEAKS_LIB": str(ROOT / "lib")},
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(rule.exists() or keep.exists())
        self.assertIn(f"chown root {self.home}/sys/gone/charging_pause", log.read_text())
        self.assertIn(f"removed {rule}", r.stdout)



class SleepWatch(unittest.TestCase):
    """charge-limit-sleep: holds a delay sleep lock; as the Frame goes to sleep it runs
    charge-limit --before-sleep, then lets go of the lock; awake, charge-limit --once, and it
    takes the lock again. (Stand-ins for jeepney and logind.)"""
    def test_sleep_and_wake(self):
        import importlib.machinery
        import importlib.util
        import types
        from unittest import mock
        fake = {n: types.ModuleType(n) for n in ("jeepney", "jeepney.bus_messages", "jeepney.io", "jeepney.io.blocking")}
        fake["jeepney"].DBusAddress = lambda path, bus_name, interface: types.SimpleNamespace(
            object_path=path, bus_name=bus_name, interface=interface)
        fake["jeepney"].MatchRule = lambda **k: k
        fake["jeepney"].MessageType = types.SimpleNamespace(method_return=2, error=3, signal=4)
        fake["jeepney"].new_method_call = lambda obj, method, sig=None, body=(): ("call", method, body)
        fake["jeepney.bus_messages"].message_bus = types.SimpleNamespace(AddMatch=lambda rule: ("match", rule))
        fake["jeepney.io.blocking"].open_dbus_connection = lambda *a, **k: None
        loader = importlib.machinery.SourceFileLoader("charge_limit_sleep", str(TWEAK / "charge-limit-sleep"))
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
        with mock.patch.dict(sys.modules, fake):
            loader.exec_module(module)

        class Lock:
            closed = False

            def close(self):
                self.closed = True

        def signal_msg(going):
            return types.SimpleNamespace(header=types.SimpleNamespace(message_type=4, fields={3: "PrepareForSleep"}),
                                         body=(going,))

        import collections
        import contextlib

        class Conn:
            """jeepney's blocking connection: signals matching a filter go to its queue, also
            while it waits for a reply (here: the Frame goes back to sleep during the lock
            request made on waking)."""
            def __init__(self):
                self.locks, self.matches = [], []
                self.inbox = [signal_msg(True), signal_msg(False)]
                self.queue = None

            @contextlib.contextmanager
            def filter(self, rule, bufsize=1):
                self.queue = collections.deque(maxlen=bufsize)
                yield self.queue

            def send_and_get_reply(self, msg):
                if msg[0] == "match":
                    self.matches.append(msg[1])
                    return types.SimpleNamespace(header=types.SimpleNamespace(message_type=2), body=())
                self.assertion = msg
                lock = Lock()
                self.locks.append(lock)
                if len(self.locks) == 2:
                    self.queue.append(signal_msg(True))       # (asleep again, before the reply)
                return types.SimpleNamespace(header=types.SimpleNamespace(message_type=2), body=(lock,))

            def recv_until_filtered(self, queue):
                if not queue:
                    if not self.inbox:
                        raise EOFError
                    queue.append(self.inbox.pop(0))
                return queue.popleft()
        conn, steps = Conn(), []

        def run(cmd, timeout):
            steps.append((cmd, [lock.closed for lock in conn.locks]))
        with mock.patch.object(module.subprocess, "run", run), self.assertRaises(EOFError):
            module.watch(conn, "/x/charge-limit")
        self.assertEqual(conn.matches[0]["member"], "PrepareForSleep")
        self.assertEqual(conn.assertion[1], "Inhibit")
        self.assertEqual(conn.assertion[2][0], "sleep")
        self.assertEqual(conn.assertion[2][3], "delay")
        # before sleep: --before-sleep while the lock is still held; awake: a new lock first, then
        # --after-sleep; the sleep that came during that lock request isn't lost
        self.assertEqual(steps, [(["/x/charge-limit", "--before-sleep"], [False]),
                                 (["/x/charge-limit", "--after-sleep"], [True, False]),
                                 (["/x/charge-limit", "--before-sleep"], [True, False])])
        self.assertEqual([lock.closed for lock in conn.locks], [True, True])


if __name__ == "__main__":
    unittest.main()
