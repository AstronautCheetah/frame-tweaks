#!/usr/bin/env python3
"""What the installer window and ./install.sh share, so the two can't drift apart: the component
list, hidden rows and groups, the Run button's label, and the tweaks' settings (what can be set,
the allowed values, where they're kept).

The settings panels in VR (scroll strips' and Android Mirror's gears) save the same files with the
same values; tests/test_sft_settings.py checks they still offer what's listed here.

Command line (through ./install.sh):
  sft.py hide|unhide ID...              hide a row in the installer window (or show it again)
  sft.py hide-group|unhide-group NAME   the same for a whole group (e.g. "VR windows")
  sft.py info ID                        what the installer window's details page shows
  sft.py run-label ID                   the Run button's label (nothing if the tweak has none)
  sft.py settings ID                    current settings, and what each can be set to
  sft.py settings ID KEY=VALUE...       change them (VALUE: a listed value or its label)
  sft.py settings ID --reset            back to the defaults
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONF = Path.home() / ".config/frame-tweaks/installer"      # (before 0.5: ~/.config/steam-frame-tweaks)
HIDDEN, SHOWN = CONF / "hidden", CONF / "shown"     # SHOWN: default-hidden rows you unhid
COLLAPSED, HIDDEN_CATS = CONF / "collapsed-categories", CONF / "hidden-categories"


def components():
    rows = []
    for line in (REPO / "components.tsv").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = (line.split("\t") + [""] * 9)[:9]
        cid, title, category, deps, desc, source, author, why, flags = f
        rows.append(dict(id=cid, title=title, category=category, deps=deps.split(), desc=desc,
                         source=source, author=author, why=why, flags=set(flags.split(",")),
                         experimental=experimental(cid)))
    return rows


def experimental(cid):
    """<id>/meta's "experimental:" note (what relies on another program's internals), or ""."""
    try:
        for line in (REPO / cid / "meta").read_text().splitlines():
            if line.startswith("experimental:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def read_set(path):
    try:
        return {line.strip() for line in path.read_text().splitlines() if line.strip()}
    except OSError:
        return set()


def write_set(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{i}\n" for i in sorted(items)))


# ---- hidden rows: yours, plus defaults you haven't unhidden ----------------
def hidden(rows=None):
    defaults = {c["id"] for c in (rows or components()) if "hidden-by-default" in c["flags"]}
    return read_set(HIDDEN) | (defaults - read_set(SHOWN))


def set_hidden(cid, hide):
    rows, shown = read_set(HIDDEN), read_set(SHOWN)
    if hide:
        rows.add(cid)
        shown.discard(cid)
    else:
        rows.discard(cid)
        shown.add(cid)
    write_set(HIDDEN, rows)
    write_set(SHOWN, shown)


def set_category_hidden(category, hide):
    cats = read_set(HIDDEN_CATS)
    cats = cats | {category} if hide else cats - {category}
    write_set(HIDDEN_CATS, cats)


def run_label(cid):
    """Label from <id>/run.sh's '# label:' line, or None when there's nothing to launch."""
    run = REPO / cid / "run.sh"
    if not run.exists():
        return None
    for line in run.read_text().splitlines()[:3]:
        if line.startswith("# label:"):
            return line.split(":", 1)[1].strip()
    return "Run"


# ---- settings ---------------------------------------------------------------------------------
# id -> {file, format ("json" | "shell": KEY=VALUE lines), about, options: [(key, title,
# [(label, value)...], default)], note}. Only listed keys are written; other content is kept.
COLOURS = [("Passthrough tint", "tint"), ("Red", 0), ("Orange", 0.08), ("Yellow", 0.15), ("Green", 0.33),
           ("Cyan", 0.5), ("Sky", 0.58), ("Blue", 0.67), ("Violet", 0.75), ("Magenta", 0.83), ("Pink", 0.92)]
SETTINGS = {
    "scroll-strips": {
        "file": Path.home() / ".config/frame-tweaks/scroll-strips.json", "format": "json",
        "about": "Big strips beside each window. Press one and drag away from that point to scroll "
                 "(farther = faster; let go to stop); tap near an end to page.",
        "note": "Changes show in VR within a few seconds. Also in VR: the gear where the strips meet.",
        "options": [
            ("vertical", "Vertical strip (scrolls up and down)", [("Right", "right"), ("Left", "left"), ("Off", "off")], "right"),
            ("horizontal", "Horizontal strip (scrolls sideways)", [("Top", "top"), ("Bottom", "bottom"), ("Off", "off")], "top"),
            ("thickness", "Thickness (cm)", [(f"{v:g}", v / 100) for v in (2, 2.5, 3, 4, 5, 6, 8)], 0.04),
            ("gap", "Gap from the window (cm)", [(f"{v:g}", v / 100) for v in (0, 1, 1.5, 2, 3, 5)], 0.015),
            ("back", "Set back behind the window (cm)", [(f"{v:g}", v / 100) for v in (0, 1, 2, 3, 5)], 0.03),
            ("color", "Colour", COLOURS, "tint"),
        ],
    },
    "adb-scrcpy": {
        "file": Path.home() / ".config/frame-tweaks/phone.conf", "format": "shell",
        "about": "The phone mirror's stream and joystick scrolling.",
        "note": "Picture and frame rate apply the next time the mirror starts (or its gear's Restart "
                "stream, in VR). Joystick speed applies at once.",
        "options": [
            ("PHONE_MAX_SIZE", "Picture size (long side, pixels)", [(v, v) for v in ("720", "800", "1024", "1280", "1600", "1920")], "1024"),
            ("PHONE_BIT_RATE", "Bit rate (Mbit/s)", [("1", "1M"), ("1.5", "1500K"), ("2", "2M"), ("3", "3M"),
                                                     ("4", "4M"), ("6", "6M"), ("8", "8M")], "2M"),
            ("PHONE_MAX_FPS", "Frame rate (fps, at most; 72-144: the Steam Frame's refresh rates)",
             [(v, v) for v in ("30", "60", "72", "80", "90", "96", "108", "120", "144")], "60"),
            ("PHONE_STICK_SPEED", "Joystick scrolling", [("Slow", "8"), ("Medium", "15"), ("Fast", "25")], "15"),
        ],
    },
}


def defaults(cid):
    return {key: default for key, _, _, default in SETTINGS[cid]["options"]}


def _allowed(cid, key, value):
    return any(v == value for _, _, choices, _ in [o for o in SETTINGS[cid]["options"] if o[0] == key]
               for _, v in choices)


def read_settings(cid):
    """Current values (defaults for anything unset or not allowed)."""
    s, out = SETTINGS[cid], defaults(cid)
    if s["format"] == "json":
        try:
            raw = json.loads(s["file"].read_text())
        except (OSError, ValueError):
            raw = {}
    else:
        raw = {}
        try:
            for line in s["file"].read_text().splitlines():
                k, eq, v = line.partition("=")
                if eq:
                    raw[k.strip()] = v.strip().strip("'\"")
        except OSError:
            pass
    for key in out:
        if key in raw and _allowed(cid, key, raw[key]):
            out[key] = raw[key]
    return out


def write_settings(cid, changes, reset=False):
    """Set these keys (allowed values only; KeyError/ValueError otherwise), keeping the file's
    other content; reset: remove all of ours first (back to the defaults)."""
    s = SETTINGS[cid]
    for key, value in changes.items():
        if key not in defaults(cid):
            raise KeyError(key)
        if not _allowed(cid, key, value):
            raise ValueError(f"{key}={value}")
    path = s["file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if s["format"] == "json":
        try:
            raw = json.loads(path.read_text())
            raw = raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            raw = {}
        if reset:
            raw = {k: v for k, v in raw.items() if k not in defaults(cid)}
        raw.update(changes)
        path.write_text(json.dumps(raw) + "\n")
        return
    try:
        lines = path.read_text().splitlines()
    except OSError:
        lines = []
    out, done = [], set()
    for line in lines:
        k = line.partition("=")[0].strip()
        if k in defaults(cid) and (reset or k in changes):
            if k in changes and k not in done:
                out.append(f"{k}={changes[k]}")
                done.add(k)
            continue
        out.append(line)
    out += [f"{k}={v}" for k, v in changes.items() if k not in done]
    path.write_text("".join(f"{line}\n" for line in out))


def parse_value(cid, key, text):
    """A value from the command line: a listed value, or its label (case and spaces ignored)."""
    norm = lambda t: str(t).replace(" ", "").lower()
    for k, _, choices, _ in SETTINGS[cid]["options"]:
        if k == key:
            for label, value in choices:
                if norm(text) in (norm(value), norm(label)):
                    return value
            raise ValueError(f"{key}: {text!r} isn't one of: {', '.join(label for label, _ in choices)}")
    raise KeyError(key)


# ---- command line -------------------------------------------------------------------------------
def info(cid):
    c = next((c for c in components() if c["id"] == cid), None)
    if not c:
        sys.exit(f"unknown component: {cid}")
    lines = [f"{c['title']}  ({c['category']})", "", c["desc"]]
    if c["why"]:
        lines += ["", "Why: " + c["why"]]
    if c["experimental"]:
        lines += ["", "Experimental: " + c["experimental"]]
    if c["deps"]:
        lines += ["", "Needs: " + ", ".join(c["deps"])]
    if c["author"]:
        lines += ["By: " + c["author"]]
    if c["source"]:
        lines += ["Source: " + c["source"].split("|")[-1]]
    readme = REPO / cid / "README.md"
    if readme.exists():
        lines += ["More: " + str(readme)]
    label = run_label(cid)
    if label:
        lines += [f"Run ({label}): ./install.sh run {cid}"]
    if cid in SETTINGS:
        lines += [f"Settings: ./install.sh settings {cid}"]
    return "\n".join(lines)


def show_settings(cid):
    s, cur = SETTINGS[cid], read_settings(cid)
    out = [f"{s['about']}  ({s['file']})"]
    for key, title, choices, default in s["options"]:
        label = next((lab for lab, v in choices if v == cur[key]), cur[key])
        out.append(f"  {key} = {label}{'  (default)' if cur[key] == default else ''}    # {title}: "
                   + ", ".join(lab for lab, _ in choices))
    out.append(s["note"])
    return "\n".join(out)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    ids = {c["id"] for c in components()}
    if cmd in ("hide", "unhide"):
        bad = [a for a in args if a not in ids]
        if bad or not args:
            sys.exit(f"unknown component: {' '.join(bad)}" if bad else f"{cmd} what?")
        for a in args:
            set_hidden(a, cmd == "hide")
        print(("Hidden" if cmd == "hide" else "Shown") + " in the installer window: " + " ".join(args))
    elif cmd in ("hide-group", "unhide-group"):
        cats = {c["category"] for c in components()}
        name = " ".join(args)
        if name not in cats:
            sys.exit(f"unknown group {name!r}; groups: {', '.join(sorted(cats))}")
        set_category_hidden(name, cmd == "hide-group")
        print(f"Group {name!r} " + ("hidden" if cmd == "hide-group" else "shown") + " in the installer window.")
    elif cmd == "info" and len(args) == 1:
        print(info(args[0]))
    elif cmd == "run-label" and len(args) == 1:
        print(run_label(args[0]) or "")
    elif cmd == "settings" and args:
        cid = args[0]
        if cid not in SETTINGS:
            sys.exit(f"{cid} has no settings; these do: {', '.join(SETTINGS)}")
        if args[1:] == ["--reset"]:
            write_settings(cid, {}, reset=True)
        elif args[1:]:
            changes = {}
            for a in args[1:]:
                key, eq, text = a.partition("=")
                if not eq:
                    sys.exit(f"expected KEY=VALUE, got {a!r}")
                try:
                    changes[key] = parse_value(cid, key, text)
                except KeyError:
                    sys.exit(f"{cid} has no setting {key!r}; it has: {', '.join(defaults(cid))}")
                except ValueError as e:
                    sys.exit(str(e))
            write_settings(cid, changes)
        print(show_settings(cid))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
