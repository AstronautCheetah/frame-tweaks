#!/usr/bin/env python3
"""Run tests/ several at a time (dev/check.sh tests): a process per test file, a slow file in
parts, the slowest first.

One after another, the tests take minutes: most of them run real scripts and wait on them. How
long each test took last time is kept in .cache/test-durations.json (not committed) to split and
order them; without it, each counts as a second. A test class with run_alone = True (one that
watches what the whole machine does, such as new files in /tmp) runs after the rest, by itself.
A part's output is shown when it fails (with -v, always). Run with the Python that has PyQt6,
as dev/check.sh does.

VR comes first. The tests run at the lowest CPU and disk priority, and while the Frame's headset
is worn, one at a time, on the core VR's real-time threads use least: on every core they made
VR stutter enough to make its wearer sick. The headset is looked at every second: put on during
a run, the tests running move to that core and no more start; taken off, they use every core
again. FRAME_TWEAKS_CHECKS=vr keeps to the VR pace, =all uses every core whatever the headset.

  dev/run-tests.py [-j N] [-v]
  dev/run-tests.py --pin         the cores to keep a check on now (none: any)
"""
import argparse
import concurrent.futures
import contextlib
import faulthandler
import glob
import itertools
import json
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
CACHE = ROOT / ".cache/test-durations.json"
# The Frame's headset proximity sensor, read as packs/core/wallet/app-timers does (worn: > 14).
# (FRAME_TWEAKS_PROX=FILE stands in for it, for tests.)
PROX = ([os.environ["FRAME_TWEAKS_PROX"]] if os.environ.get("FRAME_TWEAKS_PROX")
        else glob.glob("/sys/bus/iio/devices/iio:device*/in_proximity_raw"))
# Processes whose real-time threads draw and track VR: SteamVR's compositor and server,
# gamescope, the Frame's tracking service.
VR = ("vrcompositor", "vrserver", "gamescope", "XRService")


def worn():
    """The headset is on. (No sensor, not a Frame: no.)"""
    try:
        return float(Path(PROX[0]).read_text()) > 14
    except (IndexError, OSError, ValueError):
        return False


def cores(text):
    """{2, 3, 5} from "2-3,5" (a Cpus_allowed_list)."""
    out = set()
    for part in text.strip().split(","):
        a, _, b = part.partition("-")
        if a.strip().isdigit():
            out.update(range(int(a), int(b or a) + 1))
    return out


def vr_core(usable, proc="/proc"):
    """The usable core fewest of VR's real-time threads may run on (on a Frame: 7, which only the
    compositor's display thread shares; it renders on 4-6 and tracks on 2-3). The highest, if
    VR isn't running."""
    use = {c: 0 for c in usable}
    for task in glob.glob(f"{proc}/[0-9]*/task/[0-9]*"):
        try:
            if not Path(task).parent.parent.joinpath("comm").read_text().startswith(VR):
                continue
            if Path(task, "stat").read_text().rsplit(")", 1)[1].split()[38] not in ("1", "2"):
                continue                    # (not SCHED_FIFO or SCHED_RR)
            allowed = re.search(r"^Cpus_allowed_list:\s*(\S+)", Path(task, "status").read_text(), re.M)
            for c in cores(allowed[1]) if allowed else ():
                if c in use:
                    use[c] += 1
        except (OSError, IndexError):
            continue
    return min(sorted(use, reverse=True), key=use.get)


def descendants(root, proc="/proc"):
    """root's processes below it, all levels."""
    kids = {}
    for stat in glob.glob(f"{proc}/[0-9]*/stat"):
        try:
            ppid = int(Path(stat).read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            continue
        kids.setdefault(ppid, []).append(int(Path(stat).parent.name))
    out, todo = [], [root]
    while todo:
        for kid in kids.get(todo.pop(), ()):
            out.append(kid)
            todo.append(kid)
    return out


class Pace:
    """How many parts run at once, and where: every usable core while the headset is off; one
    part, on vr_core, while it's worn. A watcher reads the headset every second, and moves what
    runs to that core the moment it goes on."""

    def __init__(self, jobs, mode):
        self.usable = sorted(os.sched_getaffinity(0))
        self.jobs, self.mode = jobs, mode
        self.core = None                   # (looked for once: when the headset is first worn)
        self.vr = self.wants_vr()
        self.ever_vr, self.ever_all = self.vr, not self.vr
        self.running = 0
        self.cond = threading.Condition()
        self.done = threading.Event()      # (stops the watcher)
        if mode == "auto" and PROX:
            threading.Thread(target=self.watch, daemon=True).start()

    def wants_vr(self):
        return self.mode == "vr" or (self.mode == "auto" and worn())

    def cpus(self):
        if not self.vr:
            return set(self.usable)
        if self.core is None:
            self.core = vr_core(self.usable)
        return {self.core}

    def watch(self):
        while not self.done.wait(1):
            vr = self.wants_vr()
            if vr == self.vr:
                continue
            with self.cond:
                self.vr = vr
                self.ever_vr |= vr
                self.ever_all |= not vr
                self.cond.notify_all()
            if vr:                         # (now: what runs goes to VR's spare core)
                for pid in descendants(os.getpid()):
                    with contextlib.suppress(OSError):
                        os.sched_setaffinity(pid, self.cpus())

    @contextlib.contextmanager
    def slot(self):
        """Wait for a free place, then hold it: yields the cores to start on."""
        with self.cond:
            while self.running >= (1 if self.vr else self.jobs):
                self.cond.wait(1)
            self.running += 1
            cpus = self.cpus()
        try:
            yield cpus
        finally:
            with self.cond:
                self.running -= 1
                self.cond.notify_all()


def gentle():
    """The lowest CPU priority, and the lowest disk priority that still gets a turn (idle could
    wait out a busy disk, and a test time out), for this process and all it starts."""
    with contextlib.suppress(OSError):
        os.setpriority(os.PRIO_PROCESS, 0, 19)
    with contextlib.suppress(OSError):
        subprocess.run(["ionice", "-c", "2", "-n", "7", "-p", str(os.getpid())], stderr=subprocess.DEVNULL)


def discover():
    """Every test's id (test_x.Class.test_y) and whether it runs alone, in the order unittest
    finds them. (A file that can't be imported comes as its name: its own run says why.)"""
    sys.path.insert(0, str(TESTS))

    def walk(suite):
        for t in suite:
            if isinstance(t, unittest.TestSuite):
                yield from walk(t)
            elif t.id().startswith("unittest.loader._FailedTest."):
                yield t.id().rsplit(".", 1)[1], False
            else:
                yield t.id(), bool(getattr(t, "run_alone", False))
    return list(walk(unittest.defaultTestLoader.discover(str(TESTS), top_level_dir=str(TESTS))))


def plan(ids, took, jobs, whole=()):
    """The parts, slowest first: each file whole, or, if it would take more than half a core's
    fair share, in parts of about that size (tests in their order, so a class mostly stays
    together). whole: the files all of whose tests are in ids (a part may name them)."""
    def est(tid):
        return took.get(tid, 1.0)
    files = {}
    for tid in ids:
        files.setdefault(tid.split(".")[0], []).append(tid)
    limit = sum(map(est, ids)) / jobs / 2
    parts = []
    for name, tids in files.items():
        n = math.ceil(sum(map(est, tids)) / limit) if limit else 1
        if n <= 1 or len(tids) == 1:
            parts.append(([name] if name in whole else tids, tids))
            continue
        size, chunk = sum(map(est, tids)) / n, []
        for tid in tids:
            chunk.append(tid)
            if sum(map(est, chunk)) >= size:
                parts.append((chunk, chunk))
                chunk = []
        if chunk:
            parts.append((chunk, chunk))
    return sorted(parts, key=lambda p: -sum(map(est, p[1])))


def child(names, out, verbose):
    """Run names (files or test ids) here, and write what came of it to out as JSON."""
    faulthandler.enable()                  # (a crash shows where it was)
    sys.path.insert(0, str(TESTS))
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2 if verbose else 1).run(suite)
    took = {}
    for test, seconds in getattr(result, "collectedDurations", []):     # (Python 3.12 and later)
        m = re.search(r"\(([^)]*)\)$", test)
        if m:
            took[m[1]] = seconds
    Path(out).write_text(json.dumps({
        "run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "took": took}))
    sys.exit(not result.wasSuccessful())


def run(part, verbose, out, pace):
    names, tids = part
    with pace.slot() as cpus:
        start = time.monotonic()
        p = subprocess.Popen([sys.executable, __file__, "--child", str(out), *(["-v"] if verbose else []), *names],
                             cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        with contextlib.suppress(OSError):
            os.sched_setaffinity(p.pid, cpus)      # (what it starts keeps to them too)
        output = p.communicate()[0]
        seconds = time.monotonic() - start
    try:
        got = json.loads(out.read_text())
    except (OSError, ValueError):          # (it ended before it could say: an import failed, say)
        got = {"run": 0, "failures": 0, "errors": 1, "skipped": 0, "took": {}}
    if not got["took"] and tids:           # (an older Python: the part's time, shared out)
        got["took"] = {t: seconds / len(tids) for t in tids}
    return names, p.returncode, output, got


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-j", "--jobs", type=int, default=len(os.sched_getaffinity(0)))
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--pin", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--child", metavar="OUT", help=argparse.SUPPRESS)
    ap.add_argument("names", nargs="*", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.child:
        child(a.names, a.child, a.verbose)
    mode = os.environ.get("FRAME_TWEAKS_CHECKS", "auto")
    if mode not in ("auto", "vr", "all"):
        sys.exit(f"FRAME_TWEAKS_CHECKS={mode}: auto (the default), vr or all")
    if a.pin:                              # (dev/check.sh, for its other checks)
        vr = mode == "vr" or (mode == "auto" and worn())
        print(vr_core(sorted(os.sched_getaffinity(0))) if vr else "")
        return
    gentle()
    try:
        took = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        took = {}
    start = time.monotonic()
    pace = Pace(max(1, a.jobs), mode)
    tests = discover()
    ids = [t for t, _alone in tests]
    alone = [t for t, by_itself in tests if by_itself]
    whole = {t.split(".")[0] for t in ids} - {t.split(".")[0] for t in alone}
    parts = plan([t for t in ids if t not in alone], took, pace.jobs, whole)
    last = [(sorted({t.rsplit(".", 1)[0] for t in alone}), alone)] if alone else []
    totals = {"run": 0, "failures": 0, "errors": 0, "skipped": 0}
    failed = []
    with tempfile.TemporaryDirectory() as tmp, concurrent.futures.ThreadPoolExecutor(pace.jobs) as pool:
        running = [pool.submit(run, p, a.verbose, Path(tmp) / f"{i}.json", pace) for i, p in enumerate(parts)]
        results = (done.result() for done in concurrent.futures.as_completed(running))    # (each as it ends)
        then = (run(p, a.verbose, Path(tmp) / f"alone-{i}.json", pace) for i, p in enumerate(last))
        for names, rc, output, got in itertools.chain(results, then):
            for k in totals:
                totals[k] += got[k]
            took.update(got["took"])
            if rc or a.verbose:
                label = names[0] if len(names) == 1 else f"{names[0]} … ({len(names)} tests)"
                how = f"ended by {signal.Signals(-rc).name}" if rc < 0 else "failed" if rc else ""
                print(f"── {label}", how, flush=True)
                print(output.rstrip(), flush=True)
            if rc:
                failed.append(names[0])
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps({t: round(took[t], 3) for t in ids if t in took}, indent=0, sort_keys=True))
    pacing = (f"{pace.jobs} at a time" if not pace.ever_vr
              else f"one at a time on core {pace.core}, as FRAME_TWEAKS_CHECKS=vr says" if pace.mode == "vr"
              else f"one at a time on core {pace.core}: the headset was on" if not pace.ever_all
              else f"{pace.jobs} at a time, one on core {pace.core} while the headset was on")
    print("-" * 70)
    print(f"Ran {totals['run']} tests in {time.monotonic() - start:.1f}s ({len(parts)} parts, {pacing})")
    if failed:
        if pace.ever_vr and pace.ever_all:
            print("(The headset went on during the run, and the tests slowed down: a timeout may be that.)")
        print(f"FAILED (failures={totals['failures']}, errors={totals['errors']}): {', '.join(failed)}")
        sys.exit(1)
    print(f"OK (skipped={totals['skipped']})" if totals["skipped"] else "OK")


if __name__ == "__main__":
    main()
