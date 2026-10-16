#!/usr/bin/env python3
"""Run tests/ several at a time (dev/check.sh tests): a process per test file, a slow file in
parts, the slowest first, on as many cores as there are.

One after another, the tests take minutes: most of them run real scripts and wait on them. How
long each test took last time is kept in .cache/test-durations.json (not committed) to split and
order them; without it, each counts as a second. A test class with run_alone = True (one that
watches what the whole machine does, such as new files in /tmp) runs after the rest, by itself.
A part's output is shown when it fails (with -v, always). Run with the Python that has PyQt6,
as dev/check.sh does.

  dev/run-tests.py [-j N] [-v]
"""
import argparse
import concurrent.futures
import faulthandler
import itertools
import json
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
CACHE = ROOT / ".cache/test-durations.json"


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


def run(part, verbose, out):
    names, tids = part
    start = time.monotonic()
    p = subprocess.run([sys.executable, __file__, "--child", str(out), *(["-v"] if verbose else []), *names],
                       cwd=TESTS, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    seconds = time.monotonic() - start
    try:
        got = json.loads(out.read_text())
    except (OSError, ValueError):          # (it ended before it could say: an import failed, say)
        got = {"run": 0, "failures": 0, "errors": 1, "skipped": 0, "took": {}}
    if not got["took"] and tids:           # (an older Python: the part's time, shared out)
        got["took"] = {t: seconds / len(tids) for t in tids}
    return names, p.returncode, p.stdout, got


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cores = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    ap.add_argument("-j", "--jobs", type=int, default=cores or 2)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--child", metavar="OUT", help=argparse.SUPPRESS)
    ap.add_argument("names", nargs="*", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.child:
        child(a.names, a.child, a.verbose)
    try:
        took = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        took = {}
    start = time.monotonic()
    tests = discover()
    ids = [t for t, _alone in tests]
    alone = [t for t, by_itself in tests if by_itself]
    whole = {t.split(".")[0] for t in ids} - {t.split(".")[0] for t in alone}
    parts = plan([t for t in ids if t not in alone], took, a.jobs, whole)
    last = [(sorted({t.rsplit(".", 1)[0] for t in alone}), alone)] if alone else []
    totals = {"run": 0, "failures": 0, "errors": 0, "skipped": 0}
    failed = []
    with tempfile.TemporaryDirectory() as tmp, concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        running = [pool.submit(run, p, a.verbose, Path(tmp) / f"{i}.json") for i, p in enumerate(parts)]
        results = (done.result() for done in concurrent.futures.as_completed(running))    # (each as it ends)
        then = (run(p, a.verbose, Path(tmp) / f"alone-{i}.json") for i, p in enumerate(last))
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
    print("-" * 70)
    print(f"Ran {totals['run']} tests in {time.monotonic() - start:.1f}s ({len(parts)} parts, {a.jobs} at a time)")
    if failed:
        print(f"FAILED (failures={totals['failures']}, errors={totals['errors']}): {', '.join(failed)}")
        sys.exit(1)
    print(f"OK (skipped={totals['skipped']})" if totals["skipped"] else "OK")


if __name__ == "__main__":
    main()
