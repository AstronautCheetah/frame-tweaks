#!/usr/bin/env python3
"""The installer's pure logic, for ./install.sh: dependency order and ID checks, given the tweaks
and what each depends on. ./install.sh keeps running the tweaks' scripts, the lock, the logs and
sudo (docs/DESIGN.md, "Moving the installer to Python").

It reads the tweaks from stdin, one per line, in ./install.sh's order: ID<TAB>DEPENDENCY... (space
separated; ./install.sh deps_graph writes them from lib/sft.py registry). Nothing else is read, so
this starts fast and never touches a manifest.

  installer.py with-deps ID...    the IDs and what they need, transitively, dependencies first,
                                  no duplicates (a cycle stops where it began); one per line
  installer.py removal-order      every tweak, each before what it depends on (with-deps of all,
                                  reversed)
  installer.py first-unknown ID...  the first ID that isn't a tweak, exit 3; none: nothing, exit 0
  installer.py needed-by ID...    ID<TAB>OTHER for each tweak OTHER, not among the IDs, that
                                  depends on ID (the IDs in order, then the tweaks in order; one
                                  line per mention), for ./install.sh uninstall to check installed
"""
import sys


def parse_graph(text):
    """{id: [dependency, ...]} in the order given; blank lines are skipped. (A dict keeps that
    order: needed-by's order, and so which refusal ./install.sh prints, depends on it.)"""
    graph = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        cid, _tab, deps = line.partition("\t")
        graph[cid] = deps.split()
    return graph


def with_deps(graph, ids):
    """The ids plus their dependencies, dependencies first, no duplicates. The order is a
    depth-first post-order exactly as install.sh's recursive with_deps had it (tests/test_installer.py
    compares the two): installs ran in this order, and an order that changed would install a
    tweak's dependency after it. Iterative, so a long chain can't hit Python's recursion limit. An
    id not in the graph has no dependencies (./install.sh checks ids first)."""
    seen, out = set(), []
    for root in ids:
        if root in seen:
            continue
        seen.add(root)
        stack = [(root, iter(graph.get(root, ())))]
        while stack:
            node, rest = stack[-1]
            for d in rest:
                if d not in seen:
                    seen.add(d)
                    stack.append((d, iter(graph.get(d, ()))))
                    break
            else:
                stack.pop()
                out.append(node)
    return out


def removal_order(graph):
    """Every tweak, each before what it depends on: what uninstall all and uninstall-self go by."""
    return with_deps(graph, list(graph))[::-1]


def first_unknown(graph, ids):
    """The first id that isn't a tweak, or None. (./install.sh stops at it: only the first one
    is named, with what it's called now if it was renamed.)"""
    return next((i for i in ids if i not in graph), None)


def needed_by(graph, ids):
    """(id, other) for each tweak other, not among ids, that depends on id: ids in their order,
    then the tweaks in the graph's order, once per mention in other's dependencies, as
    install.sh's nested loops went; it stops at the first pair whose other is installed."""
    chosen = set(ids)
    return [(i, other) for i in ids for other, deps in graph.items() if other not in chosen for d in deps if d == i]


def main(argv, stdin=sys.stdin, stdout=sys.stdout):
    if not argv:
        sys.exit(__doc__)
    cmd, ids = argv[0], argv[1:]
    graph = parse_graph(stdin.read())
    if cmd == "with-deps":
        lines = with_deps(graph, ids)
    elif cmd == "removal-order" and not ids:
        lines = removal_order(graph)
    elif cmd == "first-unknown":
        bad = first_unknown(graph, ids)
        if bad is None:
            return 0
        print(bad, file=stdout)
        return 3        # (not 1: a Python failure, a traceback, is 1, and must not pass for an id)
    elif cmd == "needed-by":
        lines = [f"{i}\t{other}" for i, other in needed_by(graph, ids)]
    else:
        sys.exit(__doc__)
    if lines:           # (none: no empty line, which isn't an id)
        print("\n".join(lines), file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
