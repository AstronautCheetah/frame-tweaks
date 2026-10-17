"""dev/run-tests.py's pace: VR first. While the headset is worn, one part at a time on the core
VR's real-time threads use least; on every core, the tests made VR stutter enough to make its
wearer sick. (A fake /proc, and a file standing in for the proximity sensor.)"""
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script  # noqa: E402

rt = load_script(ROOT / "dev/run-tests.py", "run_tests")


def task(proc, pid, tid, comm, policy, allowed, ppid=1):
    """A thread in a fake /proc: its process's comm, its stat (policy: 0 normal, 2 SCHED_RR) and
    the cores it may run on."""
    d = proc / str(pid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "comm").write_text(comm + "\n")
    (d / "stat").write_text(f"{pid} ({comm}) " + " ".join(["S", str(ppid)] + ["0"] * 36 + [str(policy)] + ["0"] * 13))
    t = d / "task" / str(tid)
    t.mkdir(parents=True)
    (t / "stat").write_text(f"{tid} (thread one) " + " ".join(["S", str(ppid)] + ["0"] * 36 + [str(policy)] + ["0"] * 13))
    (t / "status").write_text(f"Name:\tx\nCpus_allowed_list:\t{allowed}\n")


class Cores(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.proc = Path(tmp.name)

    def test_lists(self):
        self.assertEqual(rt.cores("2-3,5"), {2, 3, 5})
        self.assertEqual(rt.cores("7\n"), {7})
        self.assertEqual(rt.cores(""), set())

    def test_the_core_vr_needs_least(self):
        """As on a Frame: the compositor renders on 4-6 and shows on 4-7, tracking runs on 2-3; a
        real-time thread of another program (the desktop's KWin, on 3-7) doesn't count, nor a
        compositor thread that isn't real-time."""
        task(self.proc, 100, 101, "vrcompositor", 2, "4-6")
        task(self.proc, 100, 102, "vrcompositor", 2, "4-7")
        task(self.proc, 100, 103, "vrcompositor", 0, "7")
        task(self.proc, 200, 201, "XRServiceLoopTh", 2, "2-3")
        task(self.proc, 300, 301, "kwin_wayland", 2, "3-7")
        self.assertEqual(rt.vr_core([3, 4, 5, 6, 7], str(self.proc)), 7)
        self.assertEqual(rt.vr_core([3, 4, 5, 6], str(self.proc)), 3)

    def test_without_vr_the_highest(self):
        self.assertEqual(rt.vr_core([3, 4, 5], str(self.proc)), 5)

    def test_everything_below_a_process(self):
        for pid, ppid in ((11, 10), (12, 10), (13, 12), (20, 1)):
            task(self.proc, pid, pid, "x", 0, "0", ppid)
        self.assertEqual(sorted(rt.descendants(10, str(self.proc))), [11, 12, 13])


class Pace(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.prox = Path(tmp.name) / "prox"
        self.prox.write_text("8.9\n")
        for patch in (mock.patch.object(rt, "PROX", [str(self.prox)]), mock.patch.object(rt, "vr_core", lambda usable: 7),
                      mock.patch.object(rt.os, "sched_getaffinity", lambda pid: {3, 4, 5, 6, 7})):
            patch.start()
            self.addCleanup(patch.stop)

    def test_one_at_a_time_on_vrs_core_while_the_headset_is_on(self):
        pace = rt.Pace(3, "auto")
        self.addCleanup(pace.done.set)
        with pace.slot() as cpus:
            self.assertEqual(cpus, {3, 4, 5, 6, 7})
        self.prox.write_text("17.5\n")                       # (put on)
        for _ in range(50):
            if pace.vr:
                break
            time.sleep(0.1)
        self.assertTrue(pace.vr)
        second = threading.Event()

        def another():
            with pace.slot():
                second.set()
        with pace.slot() as cpus:
            self.assertEqual(cpus, {7})
            threading.Thread(target=another, daemon=True).start()
            self.assertFalse(second.wait(1.5))              # (one at a time)
        self.assertTrue(second.wait(5))
        self.assertTrue(pace.ever_vr and pace.ever_all)

    def test_the_setting_decides_over_the_headset(self):
        self.prox.write_text("17.5\n")
        self.assertEqual(rt.Pace(3, "all").cpus(), {3, 4, 5, 6, 7})
        self.prox.write_text("8.9\n")
        self.assertEqual(rt.Pace(3, "vr").cpus(), {7})


if __name__ == "__main__":
    unittest.main()


class FromTheBugHunt(unittest.TestCase):
    """The second 2026-10-16 bug hunt: every thread pinned, a failed sensor read, a part that ends
    without its results, and Ctrl+C."""
    def test_every_thread_is_pinned(self):
        """sched_setaffinity(pid) sets one thread: a Qt test's other threads stayed on every core."""
        child = subprocess.Popen([sys.executable, "-c", "import threading, time\n"
                                  "threading.Thread(target=time.sleep, args=(30,), daemon=True).start()\n"
                                  "print('ready', flush=True); time.sleep(30)"], stdout=subprocess.PIPE, text=True)
        self.addCleanup(child.kill)
        child.stdout.readline()
        core = max(os.sched_getaffinity(0))
        rt.pin(child.pid, {core})
        tasks = os.listdir(f"/proc/{child.pid}/task")
        self.assertGreaterEqual(len(tasks), 2)
        for tid in tasks:
            self.assertEqual(os.sched_getaffinity(int(tid)), {core})

    def test_a_failed_sensor_read_keeps_what_it_said(self):
        with tempfile.TemporaryDirectory() as d:
            prox = Path(d) / "prox"
            prox.write_text("17.5\n")
            with mock.patch.object(rt, "PROX", [str(prox)]), mock.patch.object(rt, "vr_core", lambda usable: 7):
                pace = rt.Pace(3, "auto")
                pace.done.set()
                self.assertTrue(pace.vr)
                prox.write_text("")                         # (a read that fails: was "off", every core)
                self.assertIsNone(rt.worn())
                self.assertTrue(pace.wants_vr())

    def test_a_part_that_ends_without_its_results_failed(self):
        class Quiet:
            pid, returncode = os.getpid(), 0

            def communicate(self):
                return ("", None)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(rt.subprocess, "Popen", lambda *a, **k: Quiet()):
            names, rc, output, got = rt.run((["test_x"], ["test_x.A.test_a"]), False, Path(d) / "none.json",
                                            rt.Pace(1, "all"))
        self.assertEqual(rc, 1)
        self.assertIn("ended without its results", output)
        self.assertEqual(rt.signal_name(35), "signal 35")
        self.assertEqual(rt.signal_name(9), "SIGKILL")

    def test_ctrl_c_stops_the_run(self):
        """Ctrl+C killed the parts running, then every part still queued started, one after
        another, silently."""
        with tempfile.TemporaryDirectory() as d:
            tests, marks = Path(d) / "tests", Path(d) / "started"
            tests.mkdir()
            marks.mkdir()
            for i in range(5):
                (tests / f"test_slow{i}.py").write_text(
                    "import pathlib, time, unittest\n"
                    "class T(unittest.TestCase):\n"
                    f"    def test_it(self):\n        pathlib.Path({str(marks)!r}, '{i}').touch()\n"
                    "        time.sleep(30)\n")
            env = {**os.environ, "FRAME_TWEAKS_TESTS": str(tests), "FRAME_TWEAKS_CHECKS": "all"}
            runner = subprocess.Popen([sys.executable, str(ROOT / "dev/run-tests.py"), "-j", "2"], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            self.addCleanup(lambda: runner.poll() is None and os.killpg(runner.pid, signal.SIGKILL))
            for _ in range(200):
                if len(os.listdir(marks)) >= 2:
                    break
                time.sleep(0.05)
            os.killpg(runner.pid, signal.SIGINT)            # (Ctrl+C: the terminal's whole group)
            runner.communicate(timeout=15)
            time.sleep(1)
            self.assertEqual(runner.returncode, 130)
            self.assertEqual(len(os.listdir(marks)), 2)
