"""Desktop Recovery's taskbar watch (packs/core/tools/taskbar-guard) starts the taskbar again when
it closes while desktop mode runs, and only then: not when something else already started a new
one, not when desktop mode itself is ending, and not over and over for one that can't start. Run
against a pretend desktop (its processes, clock and restarts), and the program itself once with
stand-ins for pgrep, so it never sees this machine's desktop."""
import fcntl
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script, sandbox_env, stub  # noqa: E402

SCRIPT = ROOT / "packs/core/tools/taskbar-guard"
guard = load_script(SCRIPT)


class Desktop:
    """Desktop mode's KWin and plasmashell. Each wait for a process to end plays the next event:
    ("shell", seconds later), the taskbar closing; ("kwin", seconds later), desktop mode ending.
    later = {second: (name, pid or None)} starts or ends a process at that time (sleeps)."""

    def __init__(self, *events, later=None, restart_starts=True):
        self.procs = {"kwin_wayland": 10, "plasmashell": 20}
        self.zombies = {}                    # name: pid of one that ended, not collected yet (pgrep finds it)
        self.events, self.later = list(events), dict(later or {})
        self.clock, self.next_pid = 0, 100
        self.restarts, self.notices = [], []
        self.restart_starts = restart_starts

    def pid_of(self, name):
        return self.procs.get(name) or self.zombies.get(name)

    def alive(self, pid):
        return pid in self.procs.values()

    def _happen(self, upto):
        for t in sorted(t for t in self.later if t <= upto):
            name, pid = self.later.pop(t)
            if pid:
                self.procs[name] = pid
            else:
                self.procs.pop(name, None)

    def sleep(self, seconds):
        self.clock += seconds
        self._happen(self.clock)

    def now(self):
        return self.clock

    def wait_any(self, pids):
        if not self.events:
            raise AssertionError("waited with nothing left to happen")
        what, after = self.events.pop(0)
        self.clock += after
        self._happen(self.clock)
        if what == "kwin":
            self.procs.clear()
            return 10
        if what == "kwin-crash":             # kwin_wayland_wrapper starts a new one a second later
            old = self.procs.pop("kwin_wayland")
            self.later[self.clock + 1] = ("kwin_wayland", old + 1)
            return old
        pid = self.procs.pop("plasmashell")
        if what == "shell-zombie":
            self.zombies["plasmashell"] = pid
        assert pid in pids, (pid, pids)
        return pid

    def restart(self):
        self.restarts.append(self.clock)
        if self.restart_starts:
            self.next_pid += 1
            self.procs["plasmashell"] = self.next_pid

    def notify(self, text):
        self.notices.append(text)

    def watch(self):
        g = guard.Guard(pid_of=self.pid_of, alive=self.alive, wait_any=self.wait_any, sleep=self.sleep,
                        now=self.now, restart=self.restart, notify=self.notify)
        return g.run()


class Watch(unittest.TestCase):
    def test_a_closed_taskbar_is_started_again(self):
        d = Desktop(("shell", 60), ("kwin", 600))
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(len(d.restarts), 1)
        # (after waiting for another one to appear: Plasma's own restart, or the button)
        self.assertGreaterEqual(d.restarts[0] - 60, guard.GRACE)
        self.assertEqual(d.notices, [])

    def test_and_the_new_one_is_watched_too(self):
        d = Desktop(("shell", 60), ("shell", 60), ("kwin", 60))
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(len(d.restarts), 2)

    def test_one_started_by_something_else_is_left_alone(self):
        # The Restart taskbar button: the old one ends, a new one starts 3 seconds later.
        d = Desktop(("shell", 60), ("kwin", 600), later={63: ("plasmashell", 55)})
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(d.restarts, [])

    def test_desktop_mode_ending_is_not_a_closed_taskbar(self):
        # On the way out, the taskbar closes first and KWin a moment later.
        d = Desktop(("shell", 60), later={62: ("kwin_wayland", None)})
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(d.restarts, [])

    def test_it_gives_up_on_one_that_keeps_closing(self):
        d = Desktop(*[("shell", 30)] * 5)
        self.assertEqual(d.watch(), "gave up")
        self.assertEqual(len(d.restarts), guard.LIMIT)
        self.assertEqual(len(d.notices), 1)
        self.assertIn("Restart taskbar", d.notices[0])

    def test_closings_far_apart_are_all_fixed(self):
        d = Desktop(*[("shell", guard.WINDOW // 2)] * 6, ("kwin", 60))
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(len(d.restarts), 6)
        self.assertEqual(d.notices, [])

    def test_a_restart_that_fails_ends_the_watch_and_says_so(self):
        d = Desktop(("shell", 60), restart_starts=False)
        self.assertEqual(d.watch(), "no plasmashell")
        self.assertEqual(len(d.restarts), 1)
        self.assertEqual(len(d.notices), 1)
        self.assertIn("Restart taskbar", d.notices[0])

    def test_kwin_starting_again_after_a_crash_keeps_the_watch(self):
        """kwin_wayland_wrapper starts a new KWin after a crash, and plasmashell reconnects to it
        (QT_WAYLAND_RECONNECT): the watch carried on with the old KWin's pid and ended."""
        d = Desktop(("kwin-crash", 60), ("shell", 60), ("kwin", 60))
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(len(d.restarts), 1)                # (the taskbar closing later: still brought back)

    def test_a_taskbar_not_collected_yet_isnt_a_new_one(self):
        """One that ended but whose parent hasn't collected it yet: pgrep still finds it. Taken for
        a new one, the watch spun on it."""
        d = Desktop(("shell-zombie", 60), ("kwin", 600))
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(len(d.restarts), 1)

    def test_outside_desktop_mode_it_does_nothing(self):
        d = Desktop()
        d.procs.clear()
        self.assertEqual(d.watch(), "no desktop mode")
        self.assertEqual(d.restarts, [])

    def test_it_waits_for_the_taskbar_at_login(self):
        d = Desktop(("kwin", 600))
        del d.procs["plasmashell"]
        d.later = {5: ("plasmashell", 30)}
        self.assertEqual(d.watch(), "desktop mode ended")
        self.assertEqual(d.restarts, [])


class Program(unittest.TestCase):
    """The program itself, with pgrep finding nothing (no desktop mode), in a throwaway runtime
    folder."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        stubs = self.home / "stubs"
        stub(stubs, "pgrep", "exit 1")
        self.env = sandbox_env(self.home, stubs, XDG_RUNTIME_DIR=self.home)

    def run_it(self):
        return subprocess.run([sys.executable, str(SCRIPT)], env=self.env, capture_output=True, text=True, timeout=30)

    def test_it_stops_outside_desktop_mode(self):
        r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("stopped: no desktop mode", r.stdout)

    def test_one_watch_per_desktop(self):
        # (the installer starts one, and so does the next login's autostart)
        with open(self.home / "frame-tweaks-taskbar-guard.lock", "w") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            r = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()
