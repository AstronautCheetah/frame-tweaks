"""lib/installer.py: the dependency order and ID checks ./install.sh asks it for. Equivalence
tests: the bash it replaced (with_deps, and cmd_uninstall's "needed by" loops), kept here as the
reference, gives the same answers on random graphs, cycles included; and properties that hold
whatever the graph: every dependency before what needs it (no cycle), nothing twice, unknown ids
reported, never a crash. Then the command line ./install.sh uses, exit codes included.
What a status result means (read_status, status_of): the same as install.sh's status_of and the
window's status() before them, on generated results."""
import io
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import installer  # noqa: E402

# install.sh before lib/installer.py: with_deps as it was, and cmd_uninstall's check with
# is_installed answering "no" while noting each tweak it was asked about.
OLD_BASH = r'''
with_deps() {
    local -A seen=(); local out=()
    visit() {
        local id=$1 d
        [[ -n ${seen[$id]:-} ]] && return
        seen[$id]=1
        for d in ${DEPS[$id]}; do visit "$d"; done
        out+=("$id")
    }
    local id
    for id in "$@"; do visit "$id"; done
    [[ ${#out[@]} -eq 0 ]] || printf '%s\n' "${out[@]}"
}
is_installed() { printf 'asked %s\n' "$1"; return 1; }
needed_by() {
    local id other d
    for id in "$@"; do
        for other in "${IDS[@]}"; do
            for d in ${DEPS[$other]}; do
                if [[ $d == "$id" && " $* " != *" $other "* ]] && is_installed "$other"; then
                    exit 1
                fi
            done
        done
    done
}
'''


def random_graph(rng, n=None, cycles=True):
    """Ids from a small alphabet (so they meet each other), each depending on a few others: only
    later ones without cycles, any one (itself too) with them. Sometimes a dependency twice."""
    n = rng.randint(0, 12) if n is None else n
    ids = rng.sample([f"t{i}" for i in range(40)] + ["a-b", "x_1", "zz"], n)
    graph = {}
    for k, cid in enumerate(ids):
        pool = ids if cycles else ids[k + 1:]
        deps = [rng.choice(pool) for _ in range(rng.randint(0, 3))] if pool else []
        graph[cid] = deps
    return graph


def as_text(graph):
    return "".join(f"{cid}\t{' '.join(deps)}\n" for cid, deps in graph.items())


def run_cli(argv, graph):
    out = io.StringIO()
    code = installer.main(argv, stdin=io.StringIO(as_text(graph)), stdout=out)
    return code, out.getvalue()


class SameAsTheBashItReplaced(unittest.TestCase):
    def test_random_graphs(self):
        bash = shutil.which("bash")
        if not bash or subprocess.run([bash, "-c", "((BASH_VERSINFO[0] >= 4))"]).returncode:
            self.skipTest("needs bash 4 (associative arrays)")
        rng = random.Random(20261102)
        cases = []
        for _ in range(300):
            graph = random_graph(rng)
            ids = list(graph)
            asked = rng.sample(ids, rng.randint(0, len(ids))) if ids else []
            cases.append((graph, asked))
        script = [OLD_BASH]
        for graph, asked in cases:
            q = " ".join(f"[{cid}]='{' '.join(deps)}'" for cid, deps in graph.items())
            ids = " ".join(graph)
            args = " ".join(asked)
            script.append(f"declare -A DEPS=({q}); IDS=({ids})\n"
                          f"echo '#with'; with_deps {args}\n"
                          f"echo '#all'; with_deps \"${{IDS[@]}}\"\n"
                          f"echo '#needed'; ( needed_by {args} )\n"
                          "echo '#end'; unset DEPS\n")
        r = subprocess.run([bash, "-c", "".join(script)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        blocks = r.stdout.split("#end\n")[:-1]
        self.assertEqual(len(blocks), len(cases))
        for (graph, asked), block in zip(cases, blocks):
            _w, rest = block.split("#with\n")
            with_out, rest = rest.split("#all\n")
            all_out, needed_out = rest.split("#needed\n")
            msg = f"graph {graph}, ids {asked}"
            self.assertEqual(installer.with_deps(graph, asked), with_out.split(), msg)
            self.assertEqual(installer.removal_order(graph), all_out.split()[::-1], msg)
            # (the old loop asked about every pair, the new list has them all, in the same order)
            self.assertEqual([other for _i, other in installer.needed_by(graph, asked)],
                             [line.split()[1] for line in needed_out.splitlines()], msg)


# install.sh's status_of before lib/installer.py read_status, given what status.sh did: RC, its
# stdout as bash had it ($(...), trailing newlines gone), a file with its stderr, and 1 for a
# version record. t as lib/i18n.sh has it with no translation.
OLD_STATUS_BASH = r'''
t() { local f=$1; shift; if [ $# -eq 0 ]; then printf '%s' "$f"; else printf -- "$f" "$@"; fi; }
old_status() {
    local rc=$1 out=$2 err=$3 word why
    word=${out#"${out%%[![:space:]]*}"}; word=${word%%[[:space:]]*}
    if [[ $rc -gt 2 || ($rc -eq 1 && $word != missing && $word != restart && $4 == 1) ]]; then
        why=$(sed -e 's/\x1b\[[0-9;]*m//g' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$err" | grep . | tail -1)
        if [[ -n $why ]]; then out="warning  $(t 'status check failed: %s' "$why")"
        else out="warning  $(t 'status check failed')"; fi
        rc=2
    fi
    [[ -z $out ]] || printf '%s\n' "$out"
    return $rc
}
'''


def old_window_status(returncode, stdout, stderr, record):
    """gui/window_logic.py status() before lib/installer.py read_status, once status.sh had run."""
    out = stdout.strip()
    text = out.split(None, 1)[-1] if out else ""
    word = out.split(None, 1)[:1]
    if word == ["restart"] and returncode in (1, 2):
        return {2: installer.RESTART, 1: installer.UNLOAD}[returncode], text
    if returncode not in (0, 1, 2) or (returncode == 1 and word != ["missing"] and record):
        said = [line for line in re.sub(r"\x1b\[[0-9;]*m", "", stderr or "").splitlines() if line.strip()]
        return 2, ("status check failed: %s" % said[-1].strip() if said else "status check failed")
    return returncode, text


def random_result(rng, odd_breaks=True):
    """(exit code, stdout, stderr, record) as a status.sh might leave them, odd ones included;
    odd_breaks: stderr lines with \\r or \\v in them, which splitlines breaks at and bash didn't."""
    word = rng.choice(["ok", "missing", "warning", "restart", "other", "", "okay", "Missing"])
    text = rng.choice(["", "Fine", "Load it   now", "50% done", "a\tb", "über %s"])
    lead = rng.choice(["", "", " ", "\n", " \t"])
    tail = rng.choice(["", "\n", "\n\n", "  \n", "\nsecond line\n"])
    stdout = (lead + word + (rng.choice(["  ", " ", "\t"]) + text if text else "") + tail) if word or text else rng.choice(["", "\n"])
    lines = ["", "cat: x: No such file", "\x1b[1;33mwarning:\x1b[0m x", "  spaced  ", "\t", "%s and %d",
             "\x1b[31m\x1b[0m", "phone: command not found"]
    if odd_breaks:
        lines += ["50%\r100%\rdone", "trailing\r", "line\x0bwith a vertical tab"]
    stderr = "\n".join(rng.choice(lines) for _ in range(rng.randint(0, 4))) + rng.choice(["", "\n", "\n\n"])
    rc = rng.choice([0, 1, 2, 3, 4, 5, 1, 1, 2, 127, 255])
    return rc, stdout, stderr, rng.random() < 0.5


class StatusSameAsBefore(unittest.TestCase):
    def test_same_as_install_sh_status_of(self):
        bash = shutil.which("bash")
        if not bash or subprocess.run([bash, "-c", "((BASH_VERSINFO[0] >= 4))"]).returncode:
            self.skipTest("needs bash 4")
        rng = random.Random(20261103)
        cases = [random_result(rng) for _ in range(600)]
        with tempfile.TemporaryDirectory() as d:
            script = [OLD_STATUS_BASH]
            for k, (rc, stdout, stderr, record) in enumerate(cases):
                err = Path(d) / f"err{k}"
                err.write_text(stderr)
                script.append(f"out=$(printf '%s' {shlex.quote(stdout)}); old_status {rc} \"$out\" {err} {int(record)}; "
                              "echo \"#rc $?\"\n")
            # (bytes: text=True would turn status.sh's \\r into \\n)
            r = subprocess.run([bash, "-c", "".join(script)], capture_output=True, timeout=120,
                               env={**os.environ, "LC_ALL": "C.UTF-8"})
        self.assertEqual(r.returncode, 0, r.stderr)
        blocks = re.split(r"#rc (\d+)\n", r.stdout.decode())
        self.assertEqual(len(blocks), 2 * len(cases) + 1)
        for k, (rc, stdout, stderr, record) in enumerate(cases):
            want = (blocks[2 * k], int(blocks[2 * k + 1]))
            line, code = installer.status_of(rc, stdout.rstrip("\n"), stderr, record)
            self.assertEqual((line + "\n" if line else "", code), want, (rc, stdout, stderr, record))

    def test_same_as_the_window_had_it(self):
        """The window's rule split stderr into lines at \\r and \\v too (splitlines); install.sh's
        at \\n only, which read_status keeps: the one difference, left out here."""
        rng = random.Random(1103)
        for _ in range(2000):
            rc, stdout, stderr, record = random_result(rng, odd_breaks=False)
            if rng.random() < 0.1:
                rc = rng.choice([-9, -15, 126])          # (killed by a signal: Python's negative codes)
            self.assertEqual(installer.read_status(rc, stdout, stderr, record),
                             old_window_status(rc, stdout, stderr, record), (rc, stdout, stderr, record))

    def test_the_command_line(self):
        """As ./install.sh status_of runs it: stdout on stdin, stderr in a file, 10 + the status;
        bytes that aren't UTF-8 pass through."""
        rng = random.Random(311)
        cases = [(rc, out.rstrip("\n").encode(), err.encode(), rec) for rc, out, err, rec in
                 (random_result(rng) for _ in range(25))]
        cases += [(1, b"", b"cat: x: No such file\n", True), (1, b"restart  Unload it", b"", True),
                  (3, b"ok  fine", b"bad \xff\n", False), (0, b"ok  \xfe", b"", False)]
        with tempfile.TemporaryDirectory() as d:
            err_file = Path(d) / "err"
            for rc, out, err, record in cases:
                err_file.write_bytes(err)
                r = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), "status-of", str(rc),
                                    str(int(record)), str(err_file)], input=out, capture_output=True, timeout=30)
                line, code = installer.status_of(rc, out.decode("utf-8", "surrogateescape"),
                                                 err.decode("utf-8", "surrogateescape"), record)
                want = (line + "\n").encode("utf-8", "surrogateescape") if line else b""
                self.assertEqual((r.returncode, r.stdout), (10 + code, want), (rc, out, err, record, r.stderr))
            r = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), "status-of", "1", "1",
                                str(Path(d) / "gone")], input=b"", capture_output=True, timeout=30)
            # (no stderr file, as when mktemp failed: nothing said)
            self.assertEqual((r.returncode, r.stdout), (12, b"warning  status check failed\n"))


class Properties(unittest.TestCase):
    def test_dependencies_come_first_and_nothing_twice(self):
        rng = random.Random(1102)
        for _ in range(500):
            cyclic = rng.random() < 0.5
            graph = random_graph(rng, cycles=cyclic)
            asked = [rng.choice(list(graph)) for _ in range(rng.randint(0, 4))] if graph else []
            order = installer.with_deps(graph, asked)
            msg = f"graph {graph}, ids {asked}"
            self.assertEqual(len(order), len(set(order)), msg)
            closure, todo = set(), list(asked)          # (everything asked for, and what that needs)
            while todo:
                i = todo.pop()
                if i not in closure:
                    closure.add(i)
                    todo += graph.get(i, [])
            self.assertEqual(set(order), closure, msg)
            if not cyclic:
                for i in order:
                    for d in graph[i]:
                        self.assertLess(order.index(d), order.index(i), msg)
                removal = installer.removal_order(graph)
                for i in removal:
                    for d in graph[i]:
                        self.assertLess(removal.index(i), removal.index(d), msg)

    def test_a_long_chain_doesnt_reach_the_recursion_limit(self):
        n = sys.getrecursionlimit() * 3
        graph = {f"t{i}": [f"t{i + 1}"] for i in range(n)} | {f"t{n}": []}
        self.assertEqual(installer.with_deps(graph, ["t0"]), [f"t{i}" for i in range(n, -1, -1)])

    def test_unknown_ids_are_reported_never_a_crash(self):
        rng = random.Random(211)
        alphabet = "abc-_.é 0\t*?[]$'\"\\"
        for _ in range(500):
            graph = random_graph(rng)
            junk = ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 6))) for _ in range(rng.randint(0, 3))]
            asked = junk + rng.sample(list(graph), min(2, len(graph)))
            rng.shuffle(asked)
            unknown = [a for a in asked if a not in graph]
            self.assertEqual(installer.first_unknown(graph, asked), unknown[0] if unknown else None)
            code, out = run_cli(["first-unknown", *asked], graph)
            self.assertEqual((code, out), (3, unknown[0] + "\n") if unknown else (0, ""))
            installer.with_deps(graph, asked)           # (an unknown id: no dependencies)
            installer.needed_by(graph, asked)


class CommandLine(unittest.TestCase):
    GRAPH = {"wallet": [], "signal": ["wallet"], "vr": [], "pad": ["vr", "wallet"]}

    def test_with_deps_and_removal_order(self):
        self.assertEqual(run_cli(["with-deps", "pad", "signal"], self.GRAPH), (0, "vr\nwallet\npad\nsignal\n"))
        self.assertEqual(run_cli(["with-deps"], self.GRAPH), (0, ""))          # (no empty line)
        self.assertEqual(run_cli(["removal-order"], self.GRAPH), (0, "pad\nvr\nsignal\nwallet\n"))
        self.assertEqual(run_cli(["removal-order"], {}), (0, ""))

    def test_needed_by(self):
        self.assertEqual(run_cli(["needed-by", "wallet"], self.GRAPH), (0, "wallet\tsignal\nwallet\tpad\n"))
        self.assertEqual(run_cli(["needed-by", "wallet", "pad"], self.GRAPH), (0, "wallet\tsignal\n"))
        self.assertEqual(run_cli(["needed-by", "pad"], self.GRAPH), (0, ""))

    def test_through_python(self):
        """As ./install.sh runs it: a script of its own, the tweaks on stdin."""
        r = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), "first-unknown", "pad", "nope"],
                           input=as_text(self.GRAPH), capture_output=True, text=True, timeout=30)
        self.assertEqual((r.returncode, r.stdout), (3, "nope\n"))
        r = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), "bogus"],
                           input="", capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 1)               # (its usage: not 3, which ./install.sh reads as an id)



class StatusServer(unittest.TestCase):
    """installer.py status-server: what ./install.sh status_of asks while a command runs, one line
    each, answered as status-of would; texts as base64, so any byte gets through."""
    def test_answers_as_status_of_one_line_each(self):
        import base64
        with tempfile.TemporaryDirectory() as d:
            err = Path(d, "err")
            err.write_bytes(b"\x1b[31mcurl: (6) no host\x1b[0m\n")
            requests = [("0", "0", "/nonexistent", b"ok       fine"),
                        ("1", "1", str(err), b""),                          # (failed: a record, no word)
                        ("2", "0", "/nonexistent", "warning  caf\u00e9\nsecond".encode() + b"\xff"),
                        ("bad request",)]
            lines = "".join(" ".join(r[:3] + ((base64.b64encode(r[3]).decode() or "-") if r[3] else "-",)) + "\n"
                            if len(r) == 4 else r[0] + "\n" for r in requests)
            p = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), "status-server"], input=lines,
                               capture_output=True, text=True, timeout=30)
        replies = [line.split(" ", 1) for line in p.stdout.splitlines()]
        self.assertEqual(len(replies), 4, p.stdout + p.stderr)
        got = [(int(code), b"" if b64 == "-" else base64.b64decode(b64)) for code, b64 in replies]
        self.assertEqual(got[0], (10, b"ok       fine"))
        self.assertEqual(got[1], (12, b"warning  status check failed: curl: (6) no host"))
        self.assertEqual(got[2], (12, "warning  caf\u00e9\nsecond".encode() + b"\xff"))
        self.assertEqual(got[3], (1, b""))                                  # (install.sh asks status-of then)


if __name__ == "__main__":
    unittest.main()
