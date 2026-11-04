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
  installer.py status-server       status-of for many results, one per request line, while
                                  ./install.sh runs: EXIT RECORD STDERR_FILE STDOUT (base64, or
                                  -), answered with STATUS LINE (status-of's exit code, 10-12,
                                  and its line in base64, or -); one Python start for the run
  installer.py status-of EXIT RECORD STDERR_FILE
                                  a status.sh's result, its stdout on stdin: prints the line
                                  ./install.sh shows (stdout as it was, or "warning  status check
                                  failed: ..."), exits 10, 11 or 12 for status 0, 1 or 2. RECORD
                                  is 1 if the tweak has a version record, else 0.

What a tweak's files were when it was installed (docs/DESIGN.md, "Files changed since installed"):

  installer.py fingerprint DIR    the fingerprint of the tweak folder DIR, as ./install.sh records
                                  it in $STATE/fingerprints/<id> when its installer succeeds
  installer.py files-changed FINGERPRINTS
                                  of the tweaks on stdin (ID<TAB>DIR, one per line), those whose
                                  folder's fingerprint isn't the one recorded in FINGERPRINTS/<id>,
                                  one per line; a tweak without a record isn't named

The files ./install.sh writes for itself are rendered here, so a path is quoted in one place;
./install.sh writes them (write_file) and runs systemctl:

  installer.py unit tidy REPO     frame-tweaks-tidy.service, running REPO/install.sh tidy
  installer.py unit heal REPO     frame-tweaks-heal.service, running REPO/install.sh _heal
  installer.py unit menus-path    frame-tweaks-menus.path
  installer.py unit menus-service I18N_PY
                                  frame-tweaks-menus.service, running I18N_PY menus
  installer.py desktop-entry REPO the menu entry template on stdin with @REPO@ as REPO
"""
import os
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


# --- files changed since installed ------------------------------------------------------------
# A tweak's own folder only, not lib/: every tweak uses lib/common.sh, so a change there would
# flag every installed tweak at once, which is what ./install.sh update is for (it runs every
# installer again). Content, not dates: a restored backup or a fresh clone dates every file anew.
# What .gitignore leaves out is left out here too (__pycache__ and *.pyc, which Python writes next
# to a tweak's modules as they run; editors' *.swp and *~).
FINGERPRINT_SKIP = re.compile(r"\.pyc$|\.swp$|~$")


def readme_manifest(data):
    """A README's front matter (its manifest), the part of it the installer reads: the rest is
    text, partly written by dev/gen-docs.py, and a reworded paragraph is no reason to reinstall.
    No front matter: all of it (nothing to tell apart)."""
    if not data.startswith(b"---\n"):
        return data
    end = data.find(b"\n---\n", 3)
    return data if end < 0 else data[:end + 5]


def fingerprint(folder):
    """A SHA-256 of the files in folder (their paths relative to it, and contents; a symbolic
    link's target, not what it points to, which may be anywhere), in sorted order, so it's the
    same on every machine with the same files. Cheap: a tweak's folder is a few dozen kilobytes."""
    import hashlib      # (here: ./install.sh starts this module for every status result, too)
    h = hashlib.sha256()
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            if FINGERPRINT_SKIP.search(name):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, folder)
            if os.path.islink(path):
                data = b"-> " + os.fsencode(os.readlink(path))
            else:
                with open(path, "rb") as f:
                    data = f.read()
                if rel == "README.md":
                    data = readme_manifest(data)
            h.update(os.fsencode(rel) + b"\0" + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()


def files_changed(records, tweaks):
    """The ids of tweaks ((id, folder) pairs) whose folder's fingerprint isn't the one recorded in
    records/<id>. One without a record isn't named: unknown counts as "as installed" until its next
    install records one (an update installs every tweak again, so after the next one every tweak
    has one). Installs from before fingerprints were recorded have none: counted as changed, every
    one of them would say so until reinstalled by hand; recorded by a status run, a checkout pulled
    since the install would pass for what was installed (and status changes nothing). A folder that
    can't be read counts as changed: its files aren't what they were."""
    out = []
    for cid, folder in tweaks:
        try:
            with open(os.path.join(records, cid)) as f:
                recorded = f.read().strip()
        except (OSError, UnicodeDecodeError):
            continue
        if not recorded:
            continue
        try:
            now = fingerprint(folder) if os.path.isdir(folder) else None
        except OSError:
            now = None
        if now != recorded:
            out.append(cid)
    return out


# --- files ./install.sh writes ---------------------------------------------------------------
# A word systemd's command lines take as it is: anything else is quoted (systemd.syntax). A path
# with a space, written bare, split into two arguments, and the service ran a script that isn't
# there. Plain paths stay bare, so units written before this read the same and aren't rewritten.
SYSTEMD_BARE = re.compile(r"[^\s\"'\\;\x00-\x1f\x7f]+")
# (A desktop entry's Exec: the characters its spec reserves, which make an argument quoted.)
DESKTOP_RESERVED = re.compile(r"[\s\"'\\><~|&;$*?#()`]")


def systemd_word(arg):
    """arg as one word of an ExecStart= line. % starts a specifier (%h: the home folder) and $ a
    variable, in quotes too, so both are doubled; inside the quotes, backslash and " are escaped
    and control characters written as C escapes, which systemd reads back."""
    arg = arg.replace("%", "%%").replace("$", "$$")
    if SYSTEMD_BARE.fullmatch(arg):
        return arg
    special = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t", "\r": "\\r"}
    return '"' + "".join(special.get(c) or (f"\\x{ord(c):02x}" if ord(c) < 32 or ord(c) == 127 else c)
                         for c in arg) + '"'


def desktop_word(arg):
    """arg as one argument of a desktop entry's Exec= (Desktop Entry Specification, "The Exec
    key"): quoted when it has a reserved character, with " ` $ \\ escaped inside; % doubled (a
    field code otherwise: %h isn't the home folder there). Then the value's own escapes
    (backslash, newline, tab), which a reader undoes first: lib/needs.py window_command does."""
    if DESKTOP_RESERVED.search(arg):
        arg = '"' + re.sub(r'(["`$\\])', r"\\\1", arg) + '"'
    return desktop_string(arg.replace("%", "%%"))


def desktop_string(text):
    """text as a desktop entry's value (its string escapes)."""
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")


# (After= the heal: both run at a login and take the install lock without waiting, so tidy, which
# has no Restart=, lost the race to it and was skipped for that boot. ExecCondition=: after
# uninstall-self removed the checkout and kept tweaks, a unit running the gone script failed at
# each login, and the heal unit, restarted on failure, every two minutes for good; a condition
# that fails skips the unit, which isn't a failure. Not ConditionPathExists=: it takes the path
# bare, which can't hold a newline, where ExecCondition's quoted word can hold any path.)
TIDY_UNIT = """\
[Unit]
Description=Frame Tweaks: remove the tweaks this Frame no longer needs
After=frame-tweaks-heal.service

[Service]
Type=oneshot
ExecCondition=/usr/bin/test -f {script}
ExecStart=/bin/bash {script} tidy

[Install]
WantedBy=default.target
"""
# (At each login, before anything needs them: oneshot, so the tweaks' services it starts again
# come after it. On a failure, again two minutes later: at a login the network may not be up yet,
# and a venv that can't be moved offline needs PyPI.)
HEAL_UNIT = """\
[Unit]
Description=Frame Tweaks: its Python venvs moved to SteamOS's Python after an update
StartLimitIntervalSec=0

[Service]
Type=oneshot
ExecCondition=/usr/bin/test -f {script}
ExecStart=/bin/bash {script} _heal
Restart=on-failure
RestartSec=120

[Install]
WantedBy=default.target
"""
MENUS_PATH = """\
[Unit]
Description=Frame Tweaks: menu entries in the keyboard's language

[Path]
PathChanged=%h/.local/share/Steam/config/config.vdf
PathChanged=%h/.steam/registry.vdf
PathChanged=%h/.config/frame-tweaks/language

[Install]
WantedBy=default.target
"""
# (Steam saves config.vdf several times in a few seconds: started that often, the service hit
# systemd's start limit, and the path unit then gave up for good, with menus left in the old
# language. No limit, and a second's wait, so one run takes a burst of saves.)
MENUS_SERVICE = """\
[Unit]
Description=Frame Tweaks: menu entries in the keyboard's language
StartLimitIntervalSec=0

[Service]
Type=oneshot
ExecStartPre=/usr/bin/sleep 1
ExecStart=/usr/bin/python3 {script} menus
# (It rewrites only Frame Tweaks' menu entries: the rest of the system is out of its reach.)
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=-%h/.local/share/applications -%h/.local/share/frame-tweaks/launcher-originals
PrivateTmp=yes
PrivateNetwork=yes
RestrictAddressFamilies=AF_UNIX
LockPersonality=yes
RestrictRealtime=yes
RestrictNamespaces=yes
SystemCallArchitectures=native
"""


def unit(name, *args):
    """A unit's text, or None for a name or arguments it doesn't take. ./install.sh compares it
    with the file there: the same text is a unit already set up (its daemon-reload and enable
    skipped), so a change here rewrites every installed unit once."""
    if name == "tidy" and len(args) == 1:
        return TIDY_UNIT.format(script=systemd_word(args[0] + "/install.sh"))
    if name == "heal" and len(args) == 1:
        return HEAL_UNIT.format(script=systemd_word(args[0] + "/install.sh"))
    if name == "menus-path" and not args:
        return MENUS_PATH
    if name == "menus-service" and len(args) == 1:
        return MENUS_SERVICE.format(script=systemd_word(args[0]))
    return None


def desktop_entry(template, repo):
    """The menu entry template with @REPO@ as repo: in Exec=, the argument it's part of quoted as
    a whole (a space, or an & which sed read as "the match", broke the command); elsewhere as a
    plain value."""
    out = []
    for line in template.split("\n"):
        key, eq, value = line.partition("=")
        if "@REPO@" in value and key == "Exec":
            value = " ".join(desktop_word(w.replace("@REPO@", repo)) if "@REPO@" in w else w for w in value.split(" "))
        else:
            value = value.replace("@REPO@", desktop_string(repo))
        out.append(key + eq + value)
    return "\n".join(out)


def write_out(text, stdout):
    """text out as the bytes it came from: a path that isn't UTF-8 (surrogateescape, as Python
    reads its arguments) is written as it is, as sed wrote it, rather than failing the file."""
    if hasattr(stdout, "buffer"):
        stdout.flush()
        stdout.buffer.write(text.encode("utf-8", "surrogateescape"))
        stdout.buffer.flush()
    else:
        stdout.write(text)
    return 0


def main(argv, stdin=sys.stdin, stdout=sys.stdout):
    if not argv:
        sys.exit(__doc__)
    cmd, ids = argv[0], argv[1:]
    if cmd == "unit" and ids and (text := unit(*ids)) is not None:
        return write_out(text, stdout)
    if cmd == "desktop-entry" and len(ids) == 1:
        return write_out(desktop_entry(stdin.read(), ids[0]), stdout)
    if cmd == "status-of" and len(ids) == 3:
        return status_main(*ids, stdin=stdin, stdout=stdout)
    if cmd == "status-server" and not ids:
        return status_server(stdin, stdout)
    if cmd == "fingerprint" and len(ids) == 1:
        if not os.path.isdir(ids[0]):
            return 1            # (no folder, no fingerprint: ./install.sh records none)
        print(fingerprint(ids[0]), file=stdout)
        return 0
    if cmd == "files-changed" and len(ids) == 1:
        pairs = [line.split("\t", 1) for line in stdin.read().splitlines() if "\t" in line]
        for cid in files_changed(ids[0], pairs):
            print(cid, file=stdout)
        return 0
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



def status_server(stdin, stdout):
    """status-server: status-of, a request per line, until stdin ends. The texts travel as base64,
    so a status line can hold any byte, a newline included, without breaking the framing."""
    import base64
    import io
    for request in stdin:
        try:
            rc, record, err_file, out = request.split()
            body = io.BytesIO(b"" if out == "-" else base64.b64decode(out))
            answer = io.StringIO()
            code = status_main(rc, record, err_file, body, answer)
            line = answer.getvalue().removesuffix("\n").encode("utf-8", "surrogateescape")
            reply = f"{code} {base64.b64encode(line).decode() if line else '-'}"
        except (ValueError, OSError):
            reply = "1 -"           # (not 10-12: the caller runs status-of itself for this one)
        print(reply, file=stdout, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
