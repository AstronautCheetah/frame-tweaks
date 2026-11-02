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
from sft import component, current_release, release_channel
from i18n import _  # (translations: locale/README.md)

REPO = Path(__file__).resolve().parent.parent
# id -> known_issue (in its manifest). One dict, filled anew in place by the window as it reads the
# tweaks again (Window.use_tweaks, retranslate): the details page reads this same object, so
# binding the name to a new dict would leave that page with the old issues.
KNOWN_ISSUES = {}

RESTART = 3      # a status code of the window's own: installed, but SteamVR loads it only as it starts
UNLOAD = 4       # and: uninstalled, but SteamVR runs what it loaded until it restarts
UNAVAILABLE = 256    # and: its pack or folder went since the list was read (no program exits with 256)
GONE = (1, UNLOAD, UNAVAILABLE)   # the codes of a tweak that isn't installed


def status(cid):
    """(code, text): 0 ok, 1 not installed, 2 needs attention; a status.sh line "restart …" is
    RESTART (exit 2: installed) or UNLOAD (exit 1: uninstalled), waiting for a SteamVR restart.
    A status.sh that stops without saying "missing" or "restart" (a command in it failed) didn't
    find the tweak missing: installed by Frame Tweaks (its record), or with an exit code that
    isn't 0, 1 or 2, it's 2, "status check failed" (./install.sh status_of has the same rule).
    UNAVAILABLE: its pack or folder went since the window read the list."""
    c = component(cid)
    if c is None or sft.script(c, "status") is None:     # (its pack or folder went since the list was read)
        return UNAVAILABLE, _("not available any more")
    try:
        # (a check that never returns would hold a worker for good; four of them, every status)
        r = subprocess.run(sft.script(component(cid), "status"), capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 2, _("status check didn't finish (took over a minute)")
    out = r.stdout.strip()
    text = out.split(None, 1)[-1] if out else ""
    word = out.split(None, 1)[:1]
    if word == ["restart"] and r.returncode in (1, 2):
        return {2: RESTART, 1: UNLOAD}[r.returncode], text
    if r.returncode not in (0, 1, 2) or (r.returncode == 1 and word != ["missing"] and sft.installed_record(cid)):
        said = [line for line in re.sub(r"\x1b\[[0-9;]*m", "", r.stderr or "").splitlines() if line.strip()]
        return 2, (_("status check failed: %s") % said[-1].strip() if said else _("status check failed"))
    return r.returncode, text


def update_check(cid):
    """(installed, latest) when its update check (<id>/update-check.sh, or a link's version:)
    reports a newer upstream version, else None."""
    c = component(cid)
    cmd = sft.script(c, "update-check") if c else None
    if cmd is None:                                      # (its pack or folder went since the list was read)
        return None
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None
    if len(out) == 2 and version_tuple(out[1]) > version_tuple(out[0]):
        return out[0], out[1]
    return None


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
