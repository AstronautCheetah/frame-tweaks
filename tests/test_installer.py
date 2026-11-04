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
import needs  # noqa: E402

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


def systemd_split(line):
    """An ExecStart= value as systemd reads it (systemd.syntax, "Quoting"; systemd.service,
    "Command lines"), for checking what lib/installer.py writes without a systemd: words split at
    whitespace, "double" or 'single' quoted, C escapes in and out of quotes, then %% as % and $$
    as $. A specifier or variable that's left (%h, $HOME) is an error here: none may come from a
    path."""
    escapes = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v", "s": " ",
               "\\": "\\", '"': '"', "'": "'"}
    words, word, quote, i = [], None, None, 0
    while i < len(line):
        c = line[i]
        if c == "\\":
            nxt = line[i + 1:i + 2]
            if nxt == "x":
                word, i = (word or "") + chr(int(line[i + 2:i + 4], 16)), i + 4
                continue
            if nxt not in escapes:
                raise ValueError(f"bad escape in {line!r}")
            word, i = (word or "") + escapes[nxt], i + 2
            continue
        if quote:
            if c == quote:
                quote = None
            else:
                word += c
        elif c in "\"'":
            quote, word = c, word or ""
        elif c in " \t\n":
            if word is not None:
                words.append(word)
            word = None
        else:
            word = (word or "") + c
        i += 1
    if quote:
        raise ValueError(f"quote left open in {line!r}")
    if word is not None:
        words.append(word)
    out = []
    for w in words:
        parts = re.findall(r"%%|\$\$|[%$]|[^%$]+", w)
        if "%" in parts or "$" in parts:
            raise ValueError(f"a specifier or variable left in {w!r}")
        out.append("".join(p[0] if p in ("%%", "$$") else p for p in parts))
    return out


def exec_start(text, key="ExecStart"):
    return systemd_split(next(line for line in text.splitlines() if line.startswith(key + "="))[len(key) + 1:])


def random_path(rng):
    """A checkout path with what a folder name can hold: spaces, quotes, %, $, backslashes, ;,
    &, non-ASCII, a tab or a newline now and then."""
    chars = "ab-_.~ \"'%$\\;&|*?#()`<>=:@+,é漢"
    names = ["".join(rng.choice(chars + "\t\n" * (rng.random() < 0.05)) for _ in range(rng.randint(1, 8)))
             for _ in range(rng.randint(1, 4))]
    return "/" + "/".join(n.replace("/", "_") for n in names)


# The units and menu entry install.sh wrote with printf and sed before lib/installer.py did: for a
# path with nothing to quote, the text must be the same, or every installed unit is rewritten
# (and its systemctl daemon-reload and enable run) at the next install. (tidy: with the two lines
# added since, After= the heal and ExecCondition=, which rewrote each unit once on purpose.)
OLD_FILES = r"""
tidy() {
    printf '[Unit]\nDescription=Frame Tweaks: remove the tweaks this Frame no longer needs\nAfter=frame-tweaks-heal.service\n\n[Service]\nType=oneshot\nExecCondition=/usr/bin/test -f %s/install.sh\nExecStart=/bin/bash %s/install.sh tidy\n\n[Install]\nWantedBy=default.target\n' "$1" "$1"
}
menus_path() {
    printf '%s\n' "[Unit]" "Description=Frame Tweaks: menu entries in the keyboard's language" "" \
        "[Path]" "PathChanged=%h/.local/share/Steam/config/config.vdf" "PathChanged=%h/.steam/registry.vdf" \
        "PathChanged=%h/.config/frame-tweaks/language" "" \
        "[Install]" "WantedBy=default.target"
}
menus_service() {
    local py=$1
    printf '%s\n' "[Unit]" "Description=Frame Tweaks: menu entries in the keyboard's language" \
        "StartLimitIntervalSec=0" "" \
        "[Service]" "Type=oneshot" "ExecStartPre=/usr/bin/sleep 1" "ExecStart=/usr/bin/python3 $py menus" \
        "# (It rewrites only Frame Tweaks' menu entries: the rest of the system is out of its reach.)" \
        "NoNewPrivileges=yes" "ProtectSystem=strict" "ProtectHome=read-only" \
        "ReadWritePaths=-%h/.local/share/applications -%h/.local/share/frame-tweaks/launcher-originals" \
        "PrivateTmp=yes" "PrivateNetwork=yes" "RestrictAddressFamilies=AF_UNIX" "LockPersonality=yes" \
        "RestrictRealtime=yes" "RestrictNamespaces=yes" "SystemCallArchitectures=native"
}
desktop() { sed "s|@REPO@|$1|g" "$2"; }
"""
DESKTOP_TEMPLATE = ROOT / "share/applications/io.github.AstronautCheetah.FrameTweaks.desktop"


def old_file(*args):
    return subprocess.run(["bash", "-c", OLD_FILES + '"$@"', "old", *args], capture_output=True, text=True,
                          check=True, timeout=30).stdout


class GeneratedFiles(unittest.TestCase):
    """The units and menu entry ./install.sh writes for itself, rendered by lib/installer.py."""
    PLAIN = ["/home/deck/frame-tweaks", "/home/deck/.local/share/frame-tweaks/i18n/i18n.py", "/run/media/x/a-b_c.d"]

    def test_plain_paths_give_the_files_as_they_were(self):
        for path in self.PLAIN:
            self.assertEqual(installer.unit("tidy", path), old_file("tidy", path))
            self.assertEqual(installer.unit("menus-service", path), old_file("menus_service", path))
            self.assertEqual(installer.desktop_entry(DESKTOP_TEMPLATE.read_text(), path),
                             old_file("desktop", path, str(DESKTOP_TEMPLATE)))
        self.assertEqual(installer.unit("menus-path"), old_file("menus_path"))

    def test_any_path_reads_back_as_itself(self):
        """systemd reads ExecStart's path back whole (a space split it, a % began a specifier), and
        a desktop entry's Exec too, as lib/needs.py reads it; random paths, fixed seed."""
        rng = random.Random(3)
        for _ in range(2000):
            path = random_path(rng)
            with self.subTest(path=path):
                self.assertEqual(exec_start(installer.unit("tidy", path)), ["/bin/bash", path + "/install.sh", "tidy"])
                for name in ("tidy", "heal"):
                    self.assertEqual(exec_start(installer.unit(name, path), "ExecCondition"),
                                     ["/usr/bin/test", "-f", path + "/install.sh"])
                self.assertEqual(exec_start(installer.unit("menus-service", path)), ["/usr/bin/python3", path, "menus"])
                entry = installer.desktop_entry(DESKTOP_TEMPLATE.read_text(), path)
                lines = entry.split("\n")
                self.assertEqual(len(lines), len(DESKTOP_TEMPLATE.read_text().split("\n")))  # (no line broken)
                cmd = next(line for line in lines if line.startswith("Exec="))[len("Exec="):]
                self.assertEqual(needs.exec_args(cmd), ["env", "FRAME_TWEAKS_GUI=1", path + "/install.sh", "gui"])

    def test_login_units_skip_once_the_checkout_is_gone_and_tidy_waits_for_heal(self):
        # (uninstall-self can remove the checkout and keep tweaks: the heal unit then failed every
        # two minutes for good; and tidy, started with heal, lost the install lock to it)
        for name in ("tidy", "heal"):
            self.assertIn("\nExecCondition=/usr/bin/test -f /opt/ft/install.sh\n", installer.unit(name, "/opt/ft"))
        self.assertIn("\nAfter=frame-tweaks-heal.service\n", installer.unit("tidy", "/opt/ft"))

    def test_examples(self):
        self.assertEqual(installer.systemd_word("/x/frame tweaks 100%"), '"/x/frame tweaks 100%%"')
        self.assertEqual(installer.systemd_word('/x/a"b\\c$d'), '"/x/a\\"b\\\\c$$d"')
        self.assertEqual(installer.systemd_word("/x/50%"), "/x/50%%")       # (bare: % alone needs no quotes)
        self.assertEqual(installer.desktop_word("/x/frame tweaks 100%"), '"/x/frame tweaks 100%%"')
        self.assertEqual(installer.desktop_word("/x/a$b"), '"/x/a\\\\$b"')  # (\$ in quotes, then \\ for the \)

    def test_through_python(self):
        def run(*argv, stdin=""):
            r = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), *argv], input=stdin,
                               capture_output=True, text=True, timeout=30)
            return r.returncode, r.stdout
        self.assertEqual(run("unit", "tidy", "/x/a b"), (0, installer.unit("tidy", "/x/a b")))
        self.assertEqual(run("desktop-entry", "/x/a b", stdin="Exec=@REPO@/install.sh gui\n"),
                         (0, 'Exec="/x/a b/install.sh" gui\n'))
        self.assertEqual(run("unit", "nope")[0], 1)
        self.assertEqual(run("unit", "tidy")[0], 1)                         # (no path: its usage, no unit)


if __name__ == "__main__":
    unittest.main()


class FilesChanged(unittest.TestCase):
    """A tweak's fingerprint (lib/installer.py fingerprint, files_changed): what ./install.sh records
    when its installer succeeds, so status can say its files changed since. Its scripts and the
    README's manifest count; the README's text, Python's caches and editors' leftovers don't; a
    tweak with no record isn't named (installs from before records were kept)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "probe"
        (self.dir / "bin").mkdir(parents=True)
        (self.dir / "README.md").write_text("---\ntitle: Probe\nprocesses: []\n---\n# Probe\n\nWhat it does.\n")
        (self.dir / "install.sh").write_text("echo install\n")
        (self.dir / "bin/tool").write_text("echo tool\n")
        self.records = Path(self.tmp.name) / "fingerprints"
        self.records.mkdir()
        (self.records / "probe").write_text(installer.fingerprint(str(self.dir)) + "\n")

    def changed(self):
        return installer.files_changed(str(self.records), [("probe", str(self.dir))])

    def test_as_installed_is_unchanged(self):
        self.assertEqual(self.changed(), [])

    def test_a_script_changed(self):
        (self.dir / "bin/tool").write_text("echo tool, fixed\n")
        self.assertEqual(self.changed(), ["probe"])

    def test_a_file_added_removed_or_renamed(self):
        (self.dir / "uninstall.sh").write_text("echo uninstall\n")
        self.assertEqual(self.changed(), ["probe"])
        (self.dir / "uninstall.sh").unlink()
        self.assertEqual(self.changed(), [])
        (self.dir / "bin/tool").rename(self.dir / "bin/tool2")     # (same contents, another name)
        self.assertEqual(self.changed(), ["probe"])

    def test_the_manifest_counts_the_readmes_text_doesnt(self):
        readme = self.dir / "README.md"
        readme.write_text(readme.read_text().replace("What it does.", "What it does, reworded."))
        self.assertEqual(self.changed(), [])
        readme.write_text(readme.read_text().replace("processes: []", "processes: [probe-daemon]"))
        self.assertEqual(self.changed(), ["probe"])

    def test_caches_and_editor_files_dont_count(self):
        (self.dir / "__pycache__").mkdir()
        (self.dir / "__pycache__/tool.cpython-313.pyc").write_bytes(b"\0")
        (self.dir / "bin/old.pyc").write_bytes(b"\0")
        (self.dir / "install.sh~").write_text("old\n")
        (self.dir / ".install.sh.swp").write_text("swap\n")
        self.assertEqual(self.changed(), [])

    def test_no_record_isnt_changed_a_folder_gone_is(self):
        (self.records / "probe").unlink()
        self.assertEqual(self.changed(), [])                        # (unknown: as installed)
        (self.records / "probe").write_text("\n")
        self.assertEqual(self.changed(), [])
        (self.records / "probe").write_text(installer.fingerprint(str(self.dir)) + "\n")
        shutil.rmtree(self.dir)
        self.assertEqual(self.changed(), ["probe"])

    def test_the_same_files_elsewhere_have_the_same_fingerprint(self):
        """(another checkout, a restored backup: dates differ, the files don't)"""
        other = Path(self.tmp.name) / "elsewhere/probe"
        shutil.copytree(self.dir, other)
        os.utime(other / "install.sh", (0, 0))
        self.assertEqual(installer.fingerprint(str(other)), installer.fingerprint(str(self.dir)))

    def test_command_line(self):
        out = io.StringIO()
        self.assertEqual(installer.main(["fingerprint", str(self.dir)], stdout=out), 0)
        self.assertEqual(out.getvalue(), installer.fingerprint(str(self.dir)) + "\n")
        self.assertEqual(installer.main(["fingerprint", str(self.dir / "none")], stdout=io.StringIO()), 1)
        (self.dir / "install.sh").write_text("echo install, fixed\n")
        out = io.StringIO()
        stdin = io.StringIO(f"probe\t{self.dir}\nother\t{self.dir}\n")       # (other: no record)
        self.assertEqual(installer.main(["files-changed", str(self.records)], stdin=stdin, stdout=out), 0)
        self.assertEqual(out.getvalue(), "probe\n")
