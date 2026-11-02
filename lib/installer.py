#!/usr/bin/env python3
"""The installer's pure logic, for ./install.sh: dependency order and ID checks, given the tweaks
and what each depends on, and what a status.sh's result means (also the installer window's).
./install.sh keeps running the tweaks' scripts, the lock, the logs and sudo (docs/DESIGN.md,
"Moving the installer to Python").

The dependency commands read the tweaks from stdin, one per line, in ./install.sh's order:
ID<TAB>DEPENDENCY... (space separated; ./install.sh deps_graph writes them from lib/sft.py
registry). Nothing else is read, so this starts fast and never touches a manifest.

  installer.py with-deps ID...    the IDs and what they need, transitively, dependencies first,
                                  no duplicates (a cycle stops where it began); one per line
  installer.py removal-order      every tweak, each before what it depends on (with-deps of all,
                                  reversed)
  installer.py first-unknown ID...  the first ID that isn't a tweak, exit 3; none: nothing, exit 0
  installer.py needed-by ID...    ID<TAB>OTHER for each tweak OTHER, not among the IDs, that
                                  depends on ID (the IDs in order, then the tweaks in order; one
                                  line per mention), for ./install.sh uninstall to check installed
  installer.py status-of EXIT RECORD STDERR_FILE
                                  a status.sh's result, its stdout on stdin: prints the line
                                  ./install.sh shows (stdout as it was, or "warning  status check
                                  failed: ..."), exits 10, 11 or 12 for status 0, 1 or 2. RECORD
                                  is 1 if the tweak has a version record, else 0.
"""
import re
import sys

RESTART = 3      # a status of the window's own: installed, but SteamVR loads it only as it starts
UNLOAD = 4       # and: uninstalled, but SteamVR runs what it loaded until it restarts
ANSI = re.compile(r"\x1b\[[0-9;]*m")
BLANKS = " \t\n\r\x0b\x0c"    # (sed's [[:space:]], which install.sh trimmed stderr's lines with)


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


def read_status(returncode, stdout, stderr, record):
    """(code, text) for a status.sh that exited returncode, having printed stdout and stderr, for a
    tweak with a version record (record true) or without: 0 ok, 1 not installed, 2 needs
    attention; a "restart" line is RESTART (exit 2: installed) or UNLOAD (exit 1: uninstalled),
    waiting for a SteamVR restart. text is the line after its first word.
    A status.sh that stops without saying "missing" or "restart" (a command in it failed: set -e)
    didn't find the tweak missing. Installed by Frame Tweaks (its record), or with an exit code
    other than 0, 1 or 2, it's 2, "status check failed" with the last line stderr had: as "not
    installed", updates would skip it and forget-settings would delete its settings. Without a
    record, exit 1 is still not installed (a pack's status.sh may say so in words of its own).
    ./install.sh status_of and the window's status() both come here (docs/mods.md, the status
    protocol)."""
    out = stdout.strip()
    word = out.split(None, 1)[:1]
    text = out.split(None, 1)[-1] if out else ""
    if word == ["restart"] and returncode in (1, 2):
        return {2: RESTART, 1: UNLOAD}[returncode], text
    if returncode not in (0, 1, 2) or (returncode == 1 and word != ["missing"] and record):
        from i18n import _      # (here, not above: the usual answer needs no translations, and
                                # ./install.sh starts this once per tweak, so it stays a fast start)
        said = [line.strip(BLANKS) for line in ANSI.sub("", stderr or "").split("\n")]
        said = [line for line in said if line]
        return 2, (_("status check failed: %s") % said[-1] if said else _("status check failed"))
    return returncode, text


def status_of(returncode, stdout, stderr, record):
    """(line, status) as ./install.sh status_of prints and returns them: the window's RESTART is
    2 there and UNLOAD 1, and a line is status.sh's own unless the check failed (code 2 from
    another exit code), when it's the failure, as a warning line."""
    code, text = read_status(returncode, stdout, stderr, record)
    if code == 2 and returncode != 2:
        return "warning  " + text, 2
    return stdout.rstrip("\n"), {RESTART: 2, UNLOAD: 1}.get(code, code)


def main(argv, stdin=sys.stdin, stdout=sys.stdout):
    if not argv:
        sys.exit(__doc__)
    cmd, ids = argv[0], argv[1:]
    if cmd == "status-of" and len(ids) == 3:
        return status_main(*ids, stdin=stdin, stdout=stdout)
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


def status_main(returncode, record, err_file, stdin, stdout):
    """status-of: bytes not UTF-8 pass through as they came (surrogateescape), as bash passed them."""
    def text(f):
        data = f.read()
        return data.decode("utf-8", "surrogateescape") if isinstance(data, bytes) else data
    try:
        with open(err_file, "rb") as f:
            err = text(f)
    except OSError:     # (no file to read: nothing said, as bash's sed found nothing there)
        err = ""
    line, code = status_of(int(returncode), text(getattr(stdin, "buffer", stdin)), err, record == "1")
    if line:
        if hasattr(stdout, "buffer"):
            stdout.flush()
            stdout.buffer.write((line + "\n").encode("utf-8", "surrogateescape"))
            stdout.buffer.flush()
        else:
            stdout.write(line + "\n")
    # (not 0 to 2: a Python failure is 1, with its traceback, and must not pass for "not installed")
    return 10 + code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
