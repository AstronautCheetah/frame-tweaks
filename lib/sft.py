#!/usr/bin/env python3
"""What the installer window and ./install.sh share, so the two can't drift apart: the component
list, hidden rows and groups, the Run button's label, and the tweaks' settings (what can be set,
the allowed values, where they're kept).

The settings panels in VR (scroll strips' and Android Mirror's gears) save the same files with the
same values; tests/test_sft_settings.py checks they still offer what's listed here.

The tweaks themselves come from packs (docs/mods.md): each tweak's README.md front matter.

Command line (through ./install.sh):
  sft.py mods                           the packs, whether each is in use, and any problems
  sft.py mods trust|untrust PACK        use a user's pack (it runs as you), or stop using it
  sft.py mods on|off PACK               use one of Frame Tweaks' own packs, or stop using it
  sft.py mods check FOLDER              check a pack or a single tweak folder, using nothing
  sft.py mods add LINK [BRANCH|TAG]     a pack shared as a git repository: put in your packs folder,
                                        not used until you trust it
  sft.py mods update PACK               its newer version (from where it was added); trust it again
  sft.py mods updates                   which packs added from a link have a newer version
  sft.py mods remove PACK               delete one of your packs (its tweaks uninstalled first)
  sft.py hide|unhide ID...              hide a row in the installer window (or show it again)
  sft.py hide-group|unhide-group NAME   the same for a whole group (e.g. "VR environment")
  sft.py info ID                        what the installer window's details page shows
  sft.py run-label ID                   the Run button's label (nothing if the tweak has none)
  sft.py settings ID                    current settings, and what each can be set to
  sft.py settings ID KEY=VALUE...       change them (VALUE: a listed value or its label)
  sft.py settings ID --reset            back to the defaults
For ./install.sh and dev/test-tweaks.sh: registry, dir ID, deps ID, processes ID, config ID, link ID FIELD,
apps, uninstall-settings [keep|remove], leftover-settings [--delete] INSTALLED_ID..., test-list,
test-keeps ID.
"""
# (The docstring above is the usage the command line prints: it says nothing of the code's layout.
# The packs and tweaks are lib/registry.py's, adding, updating and removing packs and `mods`
# lib/userpacks.py's; sft.NAME reaches both (__getattr__). What stays here is what the window
# rebinds or tests patch as sft.NAME: the settings (SETTINGS), hidden rows, what this Frame
# doesn't need, install records, and the command line.)
import json
import getpass
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftconf  # noqa: E402
import i18n  # noqa: E402
import installer  # noqa: E402
import registry  # noqa: E402
import userpacks  # noqa: E402
from i18n import _  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def __getattr__(name):
    """sft.NAME for what lib/registry.py (packs and tweaks) and lib/userpacks.py (adding, updating,
    removing packs) hold: theirs, looked up each time. A copy made here would be a second binding,
    and a test's patch of one (registry.USER_PACKS, say) wouldn't reach the window reading the other."""
    for module in (registry, userpacks):
        if name in vars(module) and not name.startswith("__"):
            return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def build_version():
    """The exact build, as lib/common.sh ft_version says it (see there): 0.5.0, 0.5.0+3.abc1234,
    0.5.0+abc1234 without the release tag, each -dirty with local changes; VERSION alone without git."""
    try:
        v = (REPO / "VERSION").read_text().strip()
    except OSError:
        v = "dev"

    def git(*args):
        try:
            r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return r.stdout.strip() if r.returncode == 0 else None
    head = git("rev-parse", "--short", "HEAD")
    if head is None:
        return v
    dirty = "-dirty" if git("status", "--porcelain", "--untracked-files=no") else ""
    n = git("rev-list", "--count", f"refs/tags/v{v}..HEAD")
    if n is None:
        return f"{v}+{head}{dirty}"
    return f"{v}{dirty}" if n == "0" else f"{v}+{n}.{head}{dirty}"
def current_release():
    """The release this checkout is (VERSION): 0.6.3, or a test release such as 0.6.4-rc.1."""
    try:
        return (REPO / "VERSION").read_text().strip()
    except OSError:
        return "0"


# Which releases updates take: stable (vX.Y.Z), or beta, test releases (vX.Y.Z-rc.N) too. As
# lib/common.sh release_channel reads it, and ./install.sh channel (or get.sh) writes it.
CHANNEL = Path.home() / ".config/frame-tweaks/channel"


def release_channel():
    c = os.environ.get("FRAME_TWEAKS_CHANNEL") or ""
    if not c:
        try:
            c = CHANNEL.read_text().strip()
        except OSError:
            pass
    return "beta" if c == "beta" else "stable"


def set_release_channel(channel):
    CHANNEL.parent.mkdir(parents=True, exist_ok=True)
    CHANNEL.write_text(("beta" if channel == "beta" else "stable") + "\n")



# ---- what you chose: hidden rows and groups, and what an uninstall does with settings ------------
# (here, not in lib/registry.py: the window and the tests use and patch them as sft.NAME)
HIDDEN, SHOWN = registry.CONF / "hidden", registry.CONF / "shown"     # SHOWN: default-hidden rows you unhid
COLLAPSED, HIDDEN_CATS = registry.CONF / "collapsed-categories", registry.CONF / "hidden-categories"
UNINSTALL_PREF = Path(os.environ.get("FRAME_TWEAKS_UNINSTALL_FILE")             # keep (default) | remove
                      or Path.home() / ".config/frame-tweaks/uninstall-settings")


def uninstall_settings():
    """What an uninstall does with a tweak's settings: "keep" (the default) or "remove"."""
    try:
        return "remove" if UNINSTALL_PREF.read_text().strip() == "remove" else "keep"
    except OSError:
        return "keep"


def set_uninstall_settings(value):
    UNINSTALL_PREF.parent.mkdir(parents=True, exist_ok=True)
    UNINSTALL_PREF.write_text(("remove" if value == "remove" else "keep") + "\n")


def leftover_settings(installed):
    """[(tweak, path)]: the settings that tweaks not installed left behind (kept on uninstall), and
    are still there. A place an installed tweak also lists stays theirs."""
    comps = registry.components()
    used = {p for c in comps if c["id"] in installed for p in c["config"]}
    return [(c, p) for c in comps if c["id"] not in installed for p in c["config"]
            if p not in used and (lambda f: f.exists() or f.is_symlink())(Path.home() / p[2:])]


def remove_setting(p):
    """Delete one config: place (a file or a folder), given as ~/…"""
    f = Path.home() / p[2:]
    if f.is_dir() and not f.is_symlink():
        shutil.rmtree(f)
    else:
        f.unlink(missing_ok=True)


STATE = Path.home() / ".local/state/frame-tweaks"           # (install.sh's $STATE)


def apply_formerly():
    """What's kept under a tweak's former id (formerly: in its manifest) moves to its id, once:
    its install record, held, unloaded and backups entries, and hidden or shown rows; and an
    official pack turned off under a former folder name is recorded under its own. ./install.sh
    and the window run this as they start. Returns what moved."""
    moved = []
    for old, new in registry.load(refresh=True).get("renamed", {}).items():
        for sub in ("installed", "held", "unloaded", "backups"):
            src, dst = STATE / sub / old, STATE / sub / new
            if (src.exists() or src.is_symlink()) and not (dst.exists() or dst.is_symlink()):
                src.rename(dst)
                moved.append(f"{sub}/{old} -> {new}")
        for f in (HIDDEN, SHOWN):
            ids = registry.read_set(f)
            if old in ids:
                registry.write_set(f, (ids - {old}) | {new})
                moved.append(f"{f.name}: {old} -> {new}")
    off = registry.read_set(registry.OFF_PACKS)
    if off and registry.off_packs() != off:
        registry.write_set(registry.OFF_PACKS, registry.off_packs())
        moved.append(f"{registry.OFF_PACKS.name}: {' '.join(sorted(off))} -> {' '.join(sorted(registry.off_packs()))}")
    if moved:
        registry.load(refresh=True)
    return moved


# ---- not needed on this Frame ------------------------------------------------
_NOT_NEEDED = {}


def not_needed(rows=None, refresh=False):
    """{id: why} for the tweaks this Frame doesn't need: their optional needed.sh exits 1 with one
    line saying why (say, SteamOS now does it itself). It checks what the Frame has (a package's
    version, a file), not the SteamOS version, which beta and stable count differently. Such a
    tweak isn't offered: hidden in the list unless installed, skipped by ./install.sh install."""
    if refresh:
        _NOT_NEEDED.clear()
    out = {}
    for c in rows or registry.components():
        script = c["dir"] / "needed.sh" if c.get("dir") else None
        if not (script and script.is_file()):
            continue
        if c["id"] not in _NOT_NEEDED:
            try:
                r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=10)
                why = (r.stdout.strip().splitlines() or [""])[0] if r.returncode == 1 else None
                why = why or None                       # (exit 1 without a why: it failed, so offered)
            except (OSError, subprocess.SubprocessError):
                why = None                              # (can't tell: offered, as before)
            _NOT_NEEDED[c["id"]] = why
        if _NOT_NEEDED[c["id"]] is not None:
            out[c["id"]] = _NOT_NEEDED[c["id"]]
    return out


def installed_record(cid):
    return (STATE / "installed" / cid).exists()


def unfinished_update():
    """The tweaks an update hasn't installed again yet (./install.sh stale_tweaks): an install
    record from another version, not held, not linked. An update cut short (its terminal closed,
    Ctrl+C) left them, and the window then said "up to date". Only after an update cut short (its
    mark, update-unfinished, left behind): a checkout moved some other way (git pull, a developer's
    own work) isn't one, and Finish the update ran every tweak's installer again."""
    if not (STATE / "update-unfinished").exists():
        return []
    try:
        version = (REPO / "VERSION").read_text().strip()
        records = {f.name: f.read_text().strip() for f in userpacks.INSTALLED.iterdir() if f.is_file()}
    except OSError:
        return []
    held = STATE / "held"
    return sorted(c["id"] for c in registry.components()
                  if c["id"] in records and records[c["id"]] != version and not c.get("link")
                  and not (held / c["id"]).exists())


# ---- hidden rows: yours, plus defaults you haven't unhidden ----------------
def hidden(rows=None):
    rows = rows or registry.components()
    defaults = {c["id"] for c in rows if "hidden-by-default" in c["flags"]}
    defaults |= {cid for cid in not_needed(rows) if not installed_record(cid)}   # (installed: its status says)
    return registry.read_set(HIDDEN) | (defaults - registry.read_set(SHOWN))


def set_hidden(cid, hide):
    rows, shown = registry.read_set(HIDDEN), registry.read_set(SHOWN)
    if hide:
        rows.add(cid)
        shown.discard(cid)
    else:
        rows.discard(cid)
        shown.add(cid)
    registry.write_set(HIDDEN, rows)
    registry.write_set(SHOWN, shown)


_CATEGORY_NAMES = {}


def category_names(rows=None):
    """{a group's name, in English or in any language Frame Tweaks has: its English name}. Hidden
    and folded groups are kept by their English name, since the window shows them in the
    keyboard's language, which can change (one folded in Spanish stayed folded only in Spanish)."""
    english = frozenset(c.get("category_en", c["category"]) for c in (rows or registry.components()))
    if english not in _CATEGORY_NAMES:
        names = {}
        for po in sorted(i18n.LOCALE.glob("*.po")):
            names.update({i18n.Catalogue([po.stem]).gettext(e): e for e in english})
        names.update({e: e for e in english})
        _CATEGORY_NAMES[english] = names
    return _CATEGORY_NAMES[english]


def read_categories(path, rows=None):
    """The hidden (HIDDEN_CATS) or folded (COLLAPSED) groups, by English name, whatever language
    they were saved in."""
    names = category_names(rows)
    return {names.get(s, s) for s in registry.read_set(path)}


def set_category_hidden(category, hide):
    """category: its English name (or its name in any language Frame Tweaks has)."""
    category = category_names().get(category, category)
    cats = read_categories(HIDDEN_CATS)
    cats = cats | {category} if hide else cats - {category}
    registry.write_set(HIDDEN_CATS, cats)


def run_label(cid):
    """The Run button's label (run: label: in the manifest), or None when there's nothing to launch."""
    c = registry.component(cid)
    return c["run_label"] if c else None


# ---- settings ---------------------------------------------------------------------------------
# id -> {file, format ("json" | "shell": KEY=VALUE lines), about, options: [(key, title,
# [(label, value)...], default)], note}, from each tweak's settings: front matter. Only listed
# keys are written; other content is kept.
def settings_specs():
    out = {}
    for c in registry.components():
        st = c["settings"]
        if st:
            out[c["id"]] = {"file": Path(st["file"]).expanduser(), "format": st["format"],
                            "about": st.get("about", ""), "note": st.get("note", ""),
                            "options": [(o["key"], o["title"], [(ch["label"], ch["value"]) for ch in o["choices"]],
                                         o["default"]) for o in st["options"]],
                            # Buttons that run one of the tweak's own scripts (when: shown only while
                            # that setting has a value; {KEY} in the label shows it).
                            "actions": [dict(a, dir=c["dir"]) for a in st.get("actions", [])],
                            # Options shown as one tick box (two choices: on, then off).
                            "checkboxes": {o["key"] for o in st["options"] if o.get("checkbox")},
                            # Options whose number choices are hues (0..1), shown as colour circles.
                            "swatches": {o["key"] for o in st["options"] if o.get("swatches")},
                            # Other tweaks' settings shown on the same page (their own files).
                            "include": [i for i in st.get("include", []) if isinstance(i, str)]}
    return out


SETTINGS = settings_specs()


def raw_setting(cid, key):
    """A setting's value as the tweak's own scripts read it (any value, not only the choices)."""
    s = SETTINGS[cid]
    if s["format"] == "json":
        try:
            return str(json.loads(s["file"].read_text()).get(key, ""))
        except (OSError, ValueError, AttributeError):
            return ""
    if not registry.SHELL_NAME.fullmatch(key):     # (${!2} would run a subscript's $(...): a[$(cmd)])
        return ""
    try:   # a shell file: sourced, as the scripts do (values may be shell-quoted); the key goes in as $2
        return subprocess.run(["bash", "-c", '. "$1" 2>/dev/null; printf %s "${!2:-}"', "_", str(s["file"]), key],
                              capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def defaults(cid):
    return {key: default for key, _, _, default in SETTINGS[cid]["options"]}


def _allowed(cid, key, value):
    return any(v == value for _, _, choices, _ in [o for o in SETTINGS[cid]["options"] if o[0] == key]
               for _, v in choices)


def read_settings(cid):
    """Current values (defaults for anything unset or not allowed)."""
    s, out = SETTINGS[cid], defaults(cid)
    raw = ftconf.read_json(s["file"]) if s["format"] == "json" else ftconf.read_shell(s["file"])
    for key, _title, choices, _default in s["options"]:
        if key in raw:                                 # (a shell file holds text: "1280" for a listed 1280)
            out[key] = next((v for _label, v in choices if v == raw[key] or s["format"] == "shell" and str(v) == raw[key]),
                            out[key])
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
    ours = [k for k in defaults(cid) if reset and k not in changes]
    if s["format"] == "json":
        ftconf.update_json(s["file"], changes, drop=ours)
    else:                       # (quoted where they must be, so the file can be sourced: K='a b')
        ftconf.set_shell(s["file"], changes, drop=ours)


def parse_value(cid, key, text):
    """A value from the command line: a listed value, or its label (case and spaces ignored)."""
    norm = lambda t: str(t).replace(" ", "").lower()
    for k, _title, choices, _default in SETTINGS[cid]["options"]:
        if k == key:
            for label, value in choices:
                if norm(text) in (norm(value), norm(label)):
                    return value
            raise ValueError(_("{key}: {text} isn't one of: {choices}").format(
                key=key, text=repr(text), choices=", ".join(label for label, _v in choices)))
    raise KeyError(key)


# ---- command line -------------------------------------------------------------------------------
def has_password(user=None):
    """Whether your user has a password, which sudo needs (a new Frame's user has none: passwd
    sets one). False only when passwd says so (NP); True when it can't tell: sudo says for itself."""
    try:
        out = subprocess.run(["passwd", "-S", user or os.environ.get("USER") or getpass.getuser()],
                             capture_output=True, text=True, timeout=5).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return True
    return not (len(out) > 1 and out[1] == "NP")


# sudo: when and why installing it asks for the sudo password (the window tags its row sudo),
# or "homebrew": only while Homebrew isn't installed, whose installer asks (need_brew).
BREW = Path(os.environ.get("FRAME_TWEAKS_BREW") or "/home/linuxbrew/.linuxbrew/bin/brew")


def sudo_note(c):
    """When and why installing tweak c asks for the sudo password; "" when it won't (a Homebrew
    one, with Homebrew installed)."""
    if c.get("sudo") == "homebrew":
        return "" if BREW.exists() else _("once, if Homebrew isn't installed yet: its installer asks, to "
                                           "create /home/linuxbrew")
    return c.get("sudo") or ""


def info(cid):
    c = registry.component(cid)
    if not c:
        sys.exit(_("unknown component: %s") % cid)
    lines = [f"{c['title']}  ({c['category']})", "", c["what"]]
    if c["why"]:
        lines += ["", _("Why: %s") % c["why"]]
    if c["experimental"]:
        lines += ["", _("Experimental: %s") % c["experimental"]]
    if c["deps"]:
        lines += ["", _("Needs: %s") % ", ".join(c["deps"])]
    if sudo_note(c):
        lines += ["", _("Asks for your sudo password: %s") % sudo_note(c)]
    if c["author"]:
        lines += [_("By: %s") % c["author"]]
    if c["source"]:
        lines += [_("Source: %s") % c["source"].split("|")[-1]]
    if not c["official"]:
        lines += [(_("From the pack {pack} ({folder}), not part of Frame Tweaks; used instead of {other}'s")
                   if c["replaced"] else _("From the pack {pack} ({folder}), not part of Frame Tweaks")).format(
                      pack=repr(c["pack"]), folder=c["pack_dir"], other=c["replaced"])]
    lines += [_("More: %s") % c["readme"]]
    label = run_label(cid)
    if label:
        lines += [_("Run ({label}): {command}").format(label=label, command=f"./install.sh run {cid}")]
    if cid in SETTINGS:
        lines += [_("Settings: %s") % f"./install.sh settings {cid}"]
    return "\n".join(lines)


def mods(args):
    """./install.sh mods (lib/userpacks.py); anything it doesn't take prints this file's usage."""
    userpacks.mods(args, __doc__)


def show_settings(cid):
    s, cur = SETTINGS[cid], read_settings(cid)
    out = [f"{s['about']}  ({s['file']})"]
    for key, title, choices, default in s["options"]:
        label = next((lab for lab, v in choices if v == cur[key]), cur[key])
        mark = "  " + _("(default)") if cur[key] == default else ""
        out.append(f"  {key} = {label}{mark}    # {title}: " + ", ".join(lab for lab, _v in choices))
    out.append(s["note"])
    return "\n".join(out)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    ids = {c["id"] for c in registry.components()}
    if cmd in ("hide", "unhide"):
        bad = [a for a in args if a not in ids]
        if bad or not args:
            sys.exit(_("unknown component: %s") % " ".join(bad) if bad else _("%s what?") % cmd)
        for a in args:
            set_hidden(a, cmd == "hide")
        print((_("Hidden in the installer window: %s") if cmd == "hide" else
               _("Shown in the installer window: %s")) % " ".join(args))
    elif cmd in ("hide-group", "unhide-group"):
        names = category_names()                      # (its English name, or as the window shows it)
        name = " ".join(args)
        if name not in names:
            groups = sorted({c["category"] for c in registry.components()})
            sys.exit(_("unknown group {name}; groups: {groups}").format(name=repr(name), groups=", ".join(groups)))
        set_category_hidden(names[name], cmd == "hide-group")
        print((_("Group {name} hidden in the installer window.") if cmd == "hide-group" else
               _("Group {name} shown in the installer window.")).format(name=repr(name)))
    elif cmd == "mods":
        mods(args)
    elif cmd == "not-needed":                   # ID<TAB>why, for the tweaks this Frame doesn't need
        for cid, why in not_needed().items():
            print(f"{cid}\t{why}")
    elif cmd == "renamed" and len(args) == 1:   # a tweak's former id (formerly:): its id now
        new = registry.load().get("renamed", {}).get(args[0])
        sys.exit(1) if not new else print(new)
    elif cmd == "apply-formerly":               # move what's kept under former ids (./install.sh registry does it too)
        print("\n".join(apply_formerly()))
    elif cmd == "known-ids" and not args:
        # (every pack's tweaks, in use or not: off, not trusted, changed; ./install.sh uninstall-self
        # tells those from tweaks no pack has any more)
        print("\n".join(sorted({t for p in registry.load()["packs"] for t in p["tweaks"]})))
    elif cmd == "registry":                     # for ./install.sh: one line per tweak, \x1f-separated
        try:                                    # (./install.sh runs this as it starts: formerly: applies first)
            apply_formerly()
        except OSError as e:
            print(f"formerly: {e}", file=sys.stderr)
        for c in registry.components():                  # (a line break in a summary would start a row of its own)
            print("\x1f".join(re.sub(r"[\n\r\x1f]", " ", f) for f in [c["id"], c["title"], " ".join(c["deps"]),
                                                                  c["desc"], str(c["dir"]), "1" if c["experimental"] else "",
                                                                  "1" if c["link"] else "", "1" if sudo_note(c) else "",
                                                                  "1" if c["when_not_needed"] == "uninstall" else ""]))
    elif cmd == "dir" and len(args) == 1:
        c = registry.component(args[0])
        sys.exit(_("unknown component: %s") % args[0]) if not c else print(c["dir"])
    elif cmd == "link" and len(args) == 2:      # for lib/link.sh: a linked project's link: field
        c = registry.component(args[0])
        if not c or not c["link"] or args[1] not in registry.LINK_KEYS + ("github", "title", "app"):
            sys.exit(_("unknown component: %s") % args[0] if not c else _("%s isn't linked") % args[0])
        value = c["link"].get(args[1], "") if args[1] in registry.LINK_KEYS + ("github",) else c[args[1]]
        print("\n".join(value) if isinstance(value, list) else value)
    elif cmd == "processes" and len(args) == 1:
        c = registry.component(args[0])
        print("\n".join(c["processes"] if c else []))
    elif cmd == "apps":                       # tweaks that install another project's app: ID<TAB>its name
        for c in registry.components():
            if c["app"]:
                print(f"{c['id']}\t{c['app']}")
    elif cmd == "config" and len(args) == 1:  # where it keeps its settings (~ = $HOME)
        c = registry.component(args[0])
        print("\n".join(c["config"] if c else []))
    elif cmd == "leftover-settings":          # [--delete] INSTALLED_ID...: what uninstalled tweaks left
        delete = args[:1] == ["--delete"]
        for c, p in leftover_settings(set(args[delete:])):
            if delete:
                remove_setting(p)
            print(f"{c['id']}\t{p}")
    elif cmd == "uninstall-settings" and len(args) <= 1:
        if args:
            if args[0] not in ("keep", "remove"):
                sys.exit(_("uninstall-settings takes keep or remove"))
            set_uninstall_settings(args[0])
        print(uninstall_settings())
    elif cmd == "deps" and len(args) == 1:      # what ID needs, transitively, dependencies first
        graph = {c["id"]: c["deps"] for c in registry.components()}
        if args[0] not in graph:
            sys.exit(_("unknown component: %s") % args[0])
        # (the same order ./install.sh installs in; it always ends with the ID itself)
        print(" ".join(installer.with_deps(graph, args)[:-1]))
    elif cmd == "test-list":                    # dev/test-tweaks.sh's default set
        import shutil
        print(" ".join(c["id"] for c in registry.components() if c["test"].get("offline")
                       and all(shutil.which(n) for n in c["test"].get("needs", []))))
    elif cmd == "test-keeps" and len(args) == 1:
        c = registry.component(args[0])
        print("\n".join(c["test"].get("keeps", []) if c else []))
    elif cmd == "info" and len(args) == 1:
        print(info(args[0]))
    elif cmd == "run-label" and len(args) == 1:
        print(run_label(args[0]) or "")
    elif cmd == "settings" and args:
        cid = args[0]
        if cid not in SETTINGS:
            sys.exit(_("{id} has no settings; these do: {ids}").format(id=cid, ids=", ".join(SETTINGS)))
        if args[1:] == ["--reset"]:
            write_settings(cid, {}, reset=True)
        elif args[1:]:
            changes = {}
            for a in args[1:]:
                key, eq, text = a.partition("=")
                if not eq:
                    sys.exit(_("expected KEY=VALUE, got %s") % repr(a))
                try:
                    changes[key] = parse_value(cid, key, text)
                except KeyError:
                    sys.exit(_("{id} has no setting {key}; it has: {keys}").format(
                        id=cid, key=repr(key), keys=", ".join(defaults(cid))))
                except ValueError as e:
                    sys.exit(str(e))
            write_settings(cid, changes)
        print(show_settings(cid))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
