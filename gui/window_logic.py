"""What the installer window works out without Qt: a tweak's status (status.sh) and how its row
says it, update checks (a tweak's update-check.sh, a known issue's app, Frame Tweaks' own
releases) and how versions sort. Run in the window's background workers: nothing here may touch a
widget."""
import json
import os
import re
import shlex
import subprocess
import urllib.request
from pathlib import Path

import sft  # (lib/ is on the path)
from installer import RESTART, UNLOAD, read_status
from sft import component, current_release, release_channel
from i18n import _  # (translations: locale/README.md)

REPO = Path(__file__).resolve().parent.parent
# id -> known_issue (in its manifest). One dict, filled anew in place by the window as it reads the
# tweaks again (Window.use_tweaks, retranslate): the details page reads this same object, so
# binding the name to a new dict would leave that page with the old issues.
KNOWN_ISSUES = {}

# Status codes beyond status.sh's 0, 1 and 2: RESTART and UNLOAD (lib/installer.py read_status), and
UNAVAILABLE = 256    # its pack or folder went since the list was read (no program exits with 256)
GONE = (1, UNLOAD, UNAVAILABLE)   # the codes of a tweak that isn't installed


RUN_LABELS = {}      # id -> what its run-label.sh printed at its last status check (run_label)


def run_label(cid):
    """The Run button's label: what the tweak's optional run-label.sh printed at its last status
    check, a label that follows its state (the Performance Overlay's Show or Hide), else the
    manifest's (sft.run_label; None: nothing to launch)."""
    return RUN_LABELS.get(cid) or sft.run_label(cid)


def refresh_run_label(c):
    """Run the tweak's run-label.sh, if it has one, for RUN_LABELS (in the status worker, with each
    status check: the window checks a row again a few seconds after Run, so the label follows)."""
    cmd = sft.script(c, "run-label")
    if cmd is None:
        return
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().splitlines() if r.returncode == 0 else []
        label = lines[0].strip() if lines else ""
    except (OSError, subprocess.SubprocessError):
        label = ""
    RUN_LABELS[c["id"]] = label or None                  # (nothing, or it failed: the manifest's)


def status(cid):
    """(code, text): what its status.sh says, as lib/installer.py read_status reads it (0 ok, 1 not
    installed, 2 needs attention, RESTART or UNLOAD waiting for a SteamVR restart; the same rule
    as ./install.sh status_of). UNAVAILABLE: its pack or folder went since the window read the
    list. Its run-label.sh, if any, is run after it (refresh_run_label)."""
    c = component(cid)
    if c is None or sft.script(c, "status") is None:     # (its pack or folder went since the list was read)
        return UNAVAILABLE, _("not available any more")
    try:
        # (a check that never returns would hold a worker for good; four of them, every status)
        r = subprocess.run(sft.script(component(cid), "status"), capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 2, _("status check didn't finish (took over a minute)")
    refresh_run_label(c)
    return read_status(r.returncode, r.stdout, r.stderr, sft.installed_record(cid))


def update_check(cid):
    """(installed, latest) when its update check (<id>/update-check.sh, or a link's version:)
    reports a newer upstream version, else None. A link with a tested version reports that too
    (lib/link.sh update-check): what its row offers is then link_offer's dict."""
    c = component(cid)
    cmd = sft.script(c, "update-check") if c else None
    if cmd is None:                                      # (its pack or folder went since the list was read)
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None
    if len(out) == 3 and c.get("link"):
        return link_offer(*out, choice=sft.link_choice(cid)[0])
    if len(out) == 2 and version_tuple(out[1]) > version_tuple(out[0]):
        return out[0], out[1]
    return None


COMMIT = re.compile(r"^[0-9a-f]{7,40}$")


def same_version(a, b):
    """The same version of a linked project: a leading v either way, and a commit the same as one
    abbreviating it (lib/link.sh same_version)."""
    a, b = ((v or "")[1:] if (v or "").startswith("v") else (v or "") for v in (a, b))
    if COMMIT.match(a) and COMMIT.match(b):
        return a.startswith(b) or b.startswith(a)
    return a == b


def link_offer(installed, newest, tested, choice=None):
    """What a linked project's row offers, from lib/link.sh update-check's "<installed> <newest>
    <tested>" (newest "-": couldn't look it up) and which one Frame Tweaks installed (choice:
    "tested", "newest" or None): None for nothing, else {"tested": the tested version, "newest":
    a newer release not yet tested to offer (or None), "to_tested": "up" when the tested one is
    newer than what's installed, "back" when what's installed is newer (or None)}.
    A commit as the tested version (a project without releases) can't be ordered: any other
    commit is newer than it, and what's installed goes back to it if it was the newest asked for."""
    newest = None if newest in (None, "", "-") else newest
    commits = bool(COMMIT.match(tested[1:] if tested.startswith("v") else tested))

    def newer(a, b):
        return not same_version(a, b) if commits else version_tuple(a) > version_tuple(b)
    offer = {"tested": tested, "newest": None, "to_tested": None}
    if newest and newer(newest, tested) and not same_version(newest, installed) and (commits or newer(newest, installed)):
        offer["newest"] = newest
    if not same_version(installed, tested):
        older = choice != "newest" if commits else version_tuple(installed) < version_tuple(tested)
        offer["to_tested"] = "up" if older else "back"
    return offer if offer["newest"] or offer["to_tested"] else None


STABLE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
ANY_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.]+))?$")
def newest_release(tags, channel="stable"):
    """Newest tag (without the leading v): stable vX.Y.Z only, or with pre-releases on beta,
    where vX.Y.Z-rc1 ranks below vX.Y.Z."""
    pattern = ANY_TAG if channel == "beta" else STABLE_TAG
    ok = [t for t in tags if pattern.match(t)]
    return max(ok, key=release_key)[1:] if ok else None


def release_key(tag):
    """Sort key for "v1.2.0" / "1.2.0-rc.1": a pre-release sorts below its final version, and the
    numbers in it count as numbers (rc.10 after rc.9), as ./install.sh's sort -V has it."""
    m = ANY_TAG.match(tag if tag.startswith("v") else "v" + tag)
    if not m:
        return (0, 0, 0, False, ())
    pre = tuple((0, int(p)) if p.isdigit() else (1, p) for p in re.findall(r"\d+|\D+", m[4] or ""))
    return (int(m[1]), int(m[2]), int(m[3]), m[4] is None, pre)


def close_prompt():
    """How the terminal of an install, update or removal closes (quoted for bash). In VR (the Steam
    session's display), a floating window has an X button below it: easier than a key when there's
    no keyboard."""
    return shlex.quote(_("Press Enter to close, or press the X button floating below to close.")
                       if os.environ.get("DISPLAY") == ":0" else _("Press Enter to close…"))


def in_terminal(proc, script):
    """Start script (bash) in a Konsole window of its own, through a shell that waits for it: proc
    finishes when the terminal closes, and closing this window (which kills proc) leaves the
    terminal, and the install running in it, alone. (Konsole's messages go nowhere, as before:
    nothing read them, and once this window is gone a pipe to it would stop Konsole.)"""
    proc.start("bash", ["-c", 'konsole --separate -e bash -c "$1" >/dev/null 2>&1 & wait', "konsole", script])


def self_update_check():
    """Newest vX.Y.Z tag of this repo on GitHub, if newer than VERSION (needs git access); "" if
    there's none newer, None when it couldn't look (offline, say)."""
    try:
        r = subprocess.run(["git", "-C", str(REPO), "ls-remote", "--tags", "--refs", "origin", "v*"],
                           capture_output=True, text=True, timeout=15,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    tags = [line.rsplit("/", 1)[-1] for line in r.stdout.splitlines() if "refs/tags/v" in line]
    newest = newest_release(tags, release_channel())
    current = current_release()
    return newest if newest and release_key(newest) > release_key(current) else ""


def version_tuple(v):
    """Sort key for an app's version, in whatever form its project writes it (1.140.06880,
    v2.3, 0.2.0+138a59b): its numbers, then a pre-release (1.2.0-rc1, 1.2.0~beta2) below the
    final version. (Frame Tweaks' own tags: release_key.)"""
    main, sep, pre = (re.split(r"([-~])", (v or "").split("+")[0], maxsplit=1) + ["", ""])[:3]
    nums = lambda s: tuple(int(n) for n in re.findall(r"\d+", s))
    return nums(main), 0 if sep else 1, nums(pre)


def latest_release(url):
    """Newest release tag from GitHub's API, or None (offline, rate limit, ...)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"Accept": "application/vnd.github+json"}), timeout=8) as r:
            return json.load(r).get("tag_name")
    except Exception:
        return None


def status_text(code_text):
    if code_text is None:
        return _("checking…"), "checking"
    code, text = code_text
    if code not in (0, 1, 2, RESTART, UNLOAD, UNAVAILABLE):
        # (status.sh ended some other way, a command missing under set -e, say: installed, as
        # ./install.sh counts it, and worth a look)
        return "! " + _("status check failed (exit {code})").format(code=code), "warn"
    return ({0: "✔ " + text, 2: "! " + text, RESTART: "⟳ " + text, UNLOAD: "⟳ " + text,
             UNAVAILABLE: "· " + text}.get(code, "· " + _("not installed")),
            {0: "ok", 2: "warn", RESTART: "warn", UNLOAD: "warn"}.get(code, "missing"))
