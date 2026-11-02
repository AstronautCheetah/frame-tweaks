"""lib/installer.py: the dependency order and ID checks ./install.sh asks it for. Equivalence
tests: the bash it replaced (with_deps, and cmd_uninstall's "needed by" loops), kept here as the
reference, gives the same answers on random graphs, cycles included; and properties that hold
whatever the graph: every dependency before what needs it (no cycle), nothing twice, unknown ids
reported, never a crash. Then the command line ./install.sh uses, exit codes included."""
import io
import random
import shutil
import subprocess
import sys
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


if __name__ == "__main__":
    unittest.main()
