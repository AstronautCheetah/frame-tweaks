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
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest  # noqa: E402
import ftconf  # noqa: E402
import i18n  # noqa: E402
from i18n import _, ngettext  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def build_version():
    """The exact build, as lib/common.sh ft_version says it: 0.5.0, 0.5.0+3.abc1234[-dirty]."""
    try:
        d = subprocess.run(["git", "-C", str(REPO), "describe", "--tags", "--match", "v[0-9]*", "--dirty"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        d = None
    if not d or d.returncode != 0:
        try:
            return (REPO / "VERSION").read_text().strip()
        except OSError:
            return "dev"
    v = d.stdout.strip().removeprefix("v")
    m = re.fullmatch(r"(.+)-(\d+)-g([0-9a-f]+)(-dirty)?", v)
    return f"{m[1]}+{m[2]}.{m[3]}{m[4] or ''}" if m else v
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


CONF = Path.home() / ".config/frame-tweaks/installer"      # (before 0.5: ~/.config/steam-frame-tweaks)
HIDDEN, SHOWN = CONF / "hidden", CONF / "shown"     # SHOWN: default-hidden rows you unhid
COLLAPSED, HIDDEN_CATS = CONF / "collapsed-categories", CONF / "hidden-categories"
TRUSTED = CONF / "trusted-packs"                    # "<folder>\t<sha256 of its files>" per line
OFF_PACKS = CONF / "off-packs"                      # official packs turned off (folder names)

# ---- packs and tweaks -------------------------------------------------------------------------
# A pack is a folder of tweak folders, with an optional pack.md; a tweak is a folder whose
# README.md starts with front matter (docs/mods.md). Frame Tweaks' own packs (official) are loaded
# like any other, and are on unless turned off: Core (our own tweaks, and the helpers they need),
# Integrations (other projects' apps that Frame Tweaks fits to the Frame) and 3rd Party (other
# people's Frame projects and fixes, most of them linked). (Core was "Original", in
# packs/original, before 0.6.6.) A user's packs need trusting first (they run as you),
# and a tweak of theirs may take the place of one with the same id only by saying `replaces: true`.
CORE = REPO / "packs/core"
INTEGRATIONS = REPO / "packs/integrations"
THIRD_PARTY = REPO / "packs/third-party"
OFFICIAL_PACKS = [CORE, INTEGRATIONS, THIRD_PARTY]    # (also dev/i18n.py's: the packs whose text is in the template)
USER_PACKS = Path.home() / ".local/share/frame-tweaks/packs"
API = 1                                             # the newest pack api this version knows
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TEXT = ("title", "emoji", "category", "tier", "summary", "what", "why", "author",
        "changes", "access", "survives_updates", "undo")
OPTIONAL = ("source", "depends", "hidden_by_default", "experimental", "icon", "run", "processes",
            "settings", "known_issue", "wallet_apps", "test", "replaces", "upstream_readme", "config",
            "app", "link", "sudo", "formerly")
# app: the name of the other project's app the tweak installs (Claude Desktop, Full Keyboard, …).
# Uninstalling Frame Tweaks leaves those tweaks, and so their apps, unless asked to remove them.
# config: where a tweak keeps its settings (files or folders; its settings.file counts too). An
# uninstall keeps them, or removes them when the Preferences say so (UNINSTALL_PREF). Only below
# these roots: data kept elsewhere (adb's pairing keys, the dictation history, ~/.claude) stays.
CONFIG_ROOTS = ("~/.config/", "~/.var/app/", "~/.local/state/frame-tweaks/")
UNINSTALL_PREF = Path(os.environ.get("FRAME_TWEAKS_UNINSTALL_FILE")             # keep (default) | remove
                      or Path.home() / ".config/frame-tweaks/uninstall-settings")
# sudo: when and why installing it asks for the sudo password (the window tags its row sudo),
# or "homebrew": only while Homebrew isn't installed, whose installer asks (need_brew).
BREW = Path(os.environ.get("FRAME_TWEAKS_BREW") or "/home/linuxbrew/.linuxbrew/bin/brew")
# link: a project linked rather than integrated (docs/mods.md, Linking a project): Frame Tweaks runs
# its own install and uninstall commands as its README gives them, checks a path to tell whether
# it's installed, can start it (run), and links its README. Nothing of it is pinned, checked,
# copied or patched; the project's own channel is trusted. Such a tweak needs no scripts of its
# own: lib/link.sh does their part (script()). Its version: (a command printing the installed
# version) gives it an update check: the window compares it with the newest release of its GitHub
# project (github, from source.url or link.readme).
LINK_KEYS = ("install", "uninstall", "installed", "run", "readme", "restart", "version")
LINK_ACTIONS = ("install", "uninstall", "status", "run", "update-check")
LINK_NEEDS = {"run": "run", "update-check": "version"}     # (actions a link has only with that field)
LINK_HELPER = REPO / "lib/link.sh"
GITHUB_REPO = re.compile(r"github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?(?:[/#]|\s|$)")


def github_repo(*where):
    """The GitHub project (owner/name) named first in these addresses, or None."""
    m = GITHUB_REPO.search(" ".join(w for w in where if isinstance(w, str)))
    return m[1] if m else None
# upstream_readme: the README of the project a tweak installs, at the version it pins
# (dev/fetch-upstream-readmes.py copies it into upstream.md; dev/gen-docs.py appends it).
UPSTREAM_README = re.compile(r"^https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/\S+\.md$")


def translated(c):
    """A tweak's manifest text in the user's language (lib/i18n.py; the msgids are the English
    text, which dev/i18n.py puts in the template). Ids, files and values stay as they are."""
    if i18n.CATALOGUE.language is None:
        return c
    c = dict(c)
    for k in ("title", "desc", "what", "why", "run_label", "category"):
        if isinstance(c.get(k), str):
            c[k] = _(c[k])
    if c.get("sudo") and c["sudo"] != "homebrew":
        c["sudo"] = _(c["sudo"])
    st = c.get("settings")
    if st:
        st = dict(st)
        for k in ("about", "note"):
            if isinstance(st.get(k), str):
                st[k] = _(st[k])
        st["options"] = [dict(o, title=_(o["title"]), choices=[dict(ch, label=_(ch["label"])) for ch in o.get("choices", [])])
                         for o in st.get("options", [])]
        st["actions"] = [dict(a, label=_(a["label"]), about=_(a.get("about", ""))) for a in st.get("actions", [])]
        c["settings"] = st
    return c


def pack_dirs():
    """The official packs, then other folders in this checkout's packs/ (local, not published:
    e.g. packs/attic for tweaks set aside), then ~/.local/share/frame-tweaks/packs/*, then
    FRAME_TWEAKS_PACKS (folders separated by :, each a pack). All but the official ones need trust."""
    out = list(OFFICIAL_PACKS)
    out += sorted(d for d in CORE.parent.iterdir() if d.is_dir() and d not in OFFICIAL_PACKS and not d.name.startswith(".")
                  and not (d.name in former_packs() and not (d / "pack.md").exists()))   # (what an update left of one)
    if USER_PACKS.is_dir():
        out += sorted(d for d in USER_PACKS.iterdir() if d.is_dir() and not d.name.startswith("."))
    out += [Path(d).expanduser() for d in os.environ.get("FRAME_TWEAKS_PACKS", "").split(":") if d]
    seen, uniq = set(), []
    for d in out:
        r = d.resolve()
        if r not in seen and r.is_dir():
            seen.add(r)
            uniq.append(r)
    return uniq


def pack_hash(d):
    """sha256 over a pack's files (names, contents, whether they can be run) and its links
    (where they point): trust is for this content only. Each goes in as a kind, its name, a NUL,
    then a fixed-size digest or a link's target and a NUL, so two different packs can't give the
    same input. (Folders behind links aren't followed, but adding or changing a link counts.)"""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(d):
        dirs[:] = sorted(x for x in dirs if x not in (".git", "__pycache__"))
        for name in sorted(dirs + [f for f in files if f not in (".git", "__pycache__")]):
            p = os.path.join(root, name)
            rel = os.fsencode(os.path.relpath(p, d))
            if os.path.islink(p):
                h.update(b"L" + rel + b"\0" + os.fsencode(os.readlink(p)) + b"\0")
            if not os.path.isfile(p):
                continue
            try:
                with open(p, "rb") as f:
                    fh = hashlib.sha256()
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        fh.update(chunk)
                h.update(b"F" + rel + b"\0" + (b"x" if os.access(p, os.X_OK) else b"-") + fh.digest())
            except OSError:
                h.update(b"U" + rel + b"\0")             # (unreadable: not something we run)
    return h.hexdigest()


def trusted_packs():
    out = {}
    try:
        for line in TRUSTED.read_text().split("\n"):     # (not splitlines(): it also splits at \x85, \u2028…)
            path, _, digest = line.partition("\t")
            if path:
                out[path] = digest
    except OSError:
        pass
    return out


def set_trusted(d, trust):
    t = trusted_packs()
    if trust:
        t[str(Path(d).resolve())] = pack_hash(d)
    else:
        t.pop(str(Path(d).resolve()), None)
    CONF.mkdir(parents=True, exist_ok=True)
    TRUSTED.write_text("".join(f"{k}\t{v}\n" for k, v in sorted(t.items())))


def off_packs():
    """The official packs turned off, by folder name (e.g. {"third-party"}); one turned off under
    a former name (its pack.md formerly:) counts as its own."""
    former = former_packs()
    return {former.get(name, name) for name in read_set(OFF_PACKS)}


def former_packs():
    """{a former folder name: the official pack's folder now} (pack.md formerly:, e.g. Core's
    [original])."""
    return {old: d.name for d in OFFICIAL_PACKS for old in read_pack(d)[0]["formerly"]}


def set_official(d, on):
    off = off_packs() - {Path(d).name} if on else off_packs() | {Path(d).name}
    write_set(OFF_PACKS, off)


def config_path_ok(c):
    """A config: entry: a path below one of CONFIG_ROOTS, one level down at least (never a whole
    ~/.config), without .. or a ~ inside."""
    if not (isinstance(c, str) and "\n" not in c and "~" not in c[1:]):
        return False
    root = next((r for r in CONFIG_ROOTS if c.startswith(r)), None)
    rest = Path(c[len(root):]).parts if root else ()
    return bool(rest) and ".." not in rest and (root != "~/.var/app/" or len(rest) == 1)


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
    comps = components()
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


SHELL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")       # (a shell settings file's keys: variable names)


def check_settings(st, cid, where):
    errs = []
    if not isinstance(st, dict):
        return [f"{where}: settings must be a mapping"]
    f = st.get("file")
    if not (isinstance(f, str) and f.startswith("~/.config/") and len(Path(f).parts) > 2 and ".." not in Path(f).parts):
        errs.append(f"{where}: settings.file must be a file under ~/.config/")
    if st.get("format") not in ("json", "shell"):
        errs.append(f"{where}: settings.format must be json or shell")
    for k in ("about", "note"):
        if not isinstance(st.get(k, ""), str):
            errs.append(f"{where}: settings.{k} must be text")
    opts = st.get("options")
    if not isinstance(opts, list) or not opts:
        return errs + [f"{where}: settings.options must be a list"]
    for o in opts:
        if not (isinstance(o, dict) and isinstance(o.get("key"), str) and isinstance(o.get("title"), str)
                and isinstance(o.get("choices"), list) and o["choices"] and "default" in o):
            errs.append(f"{where}: each settings option needs key, title, default and choices")
            continue
        if st.get("format") == "shell" and not SHELL_NAME.fullmatch(o["key"]):
            errs.append(f"{where}: {o['key']!r}: a shell settings file's keys are variable names (A-Z, a-z, 0-9, _)")
        vals = []
        for c in o["choices"]:
            if not (isinstance(c, dict) and isinstance(c.get("label"), str) and "value" in c):
                errs.append(f"{where}: {o['key']}: each choice needs a label and a value")
            else:
                vals.append(c["value"])
        if o.get("default") not in vals:
            errs.append(f"{where}: {o['key']}: the default must be one of the choices' values")
    for o in opts:
        if isinstance(o, dict) and o.get("checkbox") and not (isinstance(o.get("choices"), list) and len(o["choices"]) == 2):
            errs.append(f"{where}: {o.get('key')}: a checkbox option needs exactly two choices (on, then off)")
    if not (isinstance(st.get("include", []), list) and all(isinstance(i, str) for i in st.get("include", []))):
        errs.append(f"{where}: settings.include must be a list of tweak ids")
    actions = st.get("actions", [])
    if not isinstance(actions, list):
        errs.append(f"{where}: settings.actions must be a list")
        actions = []
    for a in actions:
        if not (isinstance(a, dict) and isinstance(a.get("label"), str) and isinstance(a.get("script"), str)
                and not Path(a["script"]).is_absolute() and ".." not in Path(a["script"]).parts
                and isinstance(a.get("args", []), list) and all(isinstance(x, str) for x in a.get("args", []))
                and isinstance(a.get("when", ""), str) and isinstance(a.get("about", ""), str)):
            errs.append(f"{where}: each settings action needs a label and a script in the tweak's folder "
                        "(args, when, about optional)")
    return errs


def read_tweak(d):
    """(component dict, [problems]) for a tweak folder; None as the dict if it can't be used."""
    cid, where = d.name, f"{d.parent.name}/{d.name}"
    if not ID.match(cid):
        return None, [f"{where}: a tweak's folder name (its id) must be lower-case letters, digits and -"]
    try:
        data, _ = manifest.front_matter((d / "README.md").read_text())
    except (OSError, ValueError) as e:                  # (ValueError: a ManifestError, or not UTF-8)
        return None, [f"{where}/README.md: {e}"]
    errs = [f"{where}: {k} is missing (or not text)" for k in TEXT if not isinstance(data.get(k), str) or not data[k]]
    warn = [f"warning: {where}: unknown key {k!r} (ignored)" for k in data if k not in TEXT + OPTIONAL]
    if data.get("tier") not in (None, "core", "extras", "helper"):
        errs.append(f"{where}: tier must be core, extras or helper")
    deps = data.get("depends", [])
    if not (isinstance(deps, list) and all(isinstance(x, str) for x in deps)):
        errs.append(f"{where}: depends must be a list of tweak ids")
    formerly = data.get("formerly", [])
    formerly = [formerly] if isinstance(formerly, str) else formerly
    if not (isinstance(formerly, list) and all(isinstance(x, str) and ID.match(x) and x != cid for x in formerly)):
        errs.append(f"{where}: formerly must be the tweak's earlier ids, like [old-name]")
        formerly = []
    if "sudo" in data and not (isinstance(data["sudo"], str) and data["sudo"].strip()):
        errs.append(f"{where}: sudo must be text: when and why it asks for the sudo password (or homebrew)")
    link = data.get("link")
    if link is not None:
        errs += check_link(link, where)
        if isinstance(link, dict) and "version" in link and not github_repo((data.get("source") or {}).get("url"), link.get("readme")):
            errs.append(f"{where}: link.version: its newest release is looked up on GitHub: name the "
                        "project's GitHub address in source.url or link.readme")
        warn += [f"warning: {where}: link: unknown key {k!r} (ignored)" for k in (link if isinstance(link, dict) else {})
                 if k not in LINK_KEYS]
    else:
        for script in ("install.sh", "uninstall.sh", "status.sh") + (("run.sh",) if "run" in data else ()):
            if not (d / script).is_file():
                errs.append(f"{where}: {script} is missing")
    for k in ("hidden_by_default", "replaces"):
        if k in data and not isinstance(data[k], bool):
            errs.append(f"{where}: {k} must be true or false")
    if "upstream_readme" in data and not (isinstance(data["upstream_readme"], str)
                                          and UPSTREAM_README.match(data["upstream_readme"])):
        errs.append(f"{where}: upstream_readme must be a raw.githubusercontent.com URL of a .md file")
    icon = data.get("icon", {})
    if not (isinstance(icon, dict) and set(icon) <= {"file", "flatpak", "theme"} and all(isinstance(v, str) for v in icon.values())):
        errs.append(f"{where}: icon takes file, flatpak and theme")
    # (install.sh stops whatever each pattern matches: a plain text here would be one per letter)
    procs = data.get("processes") or []
    if not (isinstance(procs, list) and all(isinstance(p, str) and p.strip() and "\n" not in p for p in procs)):
        errs.append(f"{where}: processes must be a list of pgrep -f patterns, e.g. [^~/.local/bin/my-daemon]")
    if not isinstance(data.get("app", ""), str):
        errs.append(f"{where}: app must be text: the name of the app it installs")
    conf = data.get("config") or []
    if not (isinstance(conf, list) and all(config_path_ok(c) for c in conf)):
        errs.append(f"{where}: config must be a list of paths of its own under {', '.join(CONFIG_ROOTS)}, "
                    "e.g. [~/.config/my-tweak.json]")
    apps = data.get("wallet_apps") or []
    if not (isinstance(apps, list) and all(isinstance(a, str) for a in apps)):
        errs.append(f"{where}: wallet_apps must be a list of app ids")
    if not isinstance(data.get("experimental") or "", str):
        errs.append(f"{where}: experimental must be text (what relies on another program's internals)")
    for k in ("source", "run", "known_issue", "test"):
        if not isinstance(data.get(k) or {}, dict):
            errs.append(f"{where}: {k} must be a mapping, like {{key: value}}")
    if isinstance(data.get("run"), dict) and not isinstance(data["run"].get("label", ""), str):
        errs.append(f"{where}: run.label must be text")
    issue = data.get("known_issue")
    if isinstance(issue, dict) and issue and not all(isinstance(issue.get(k), str) for k in ("version", "short", "long", "latest")):
        errs.append(f"{where}: known_issue needs version, short, long and latest (text)")
    if "settings" in data:
        errs += check_settings(data["settings"], cid, where)
    if errs:
        return None, errs + warn
    src = data.get("source") or {}
    run = data.get("run") or {}
    return dict(
        id=cid, dir=d, readme=d / "README.md", title=data["title"], emoji=data["emoji"],
        category=data["category"], tier=data["tier"], deps=deps, desc=data["summary"],
        what=data["what"], why=data["why"], author=data["author"],
        source=f"{src.get('relation', 'uses')}|{src['url']}" if src.get("url") else "",
        flags={"hidden-by-default"} if data.get("hidden_by_default") else set(),
        experimental=data.get("experimental") or "", icon=icon, sudo=(data.get("sudo") or "").strip(), formerly=formerly,
        run_label=run.get("label", "Run") if (d / "run.sh").is_file() or (link or {}).get("run") else None,
        link=link_paths(link, github_repo(src.get("url"), link.get("readme"))) if link else None,
        processes=procs, settings=data.get("settings"),
        app=data.get("app") or "",
        config=list(dict.fromkeys(conf + ([data["settings"]["file"]] if data.get("settings") else []))),
        known_issue=data.get("known_issue"), wallet_apps=apps,
        upstream_readme=data.get("upstream_readme", ""),
        test=data.get("test") or {}, replaces=data.get("replaces", False),
        changes=data["changes"], access=data["access"], survives_updates=data["survives_updates"],
        undo=data["undo"]), warn


def check_link(link, where):
    """Problems with a manifest's link: (see LINK_KEYS)."""
    if not isinstance(link, dict):
        return [f"{where}: link must be a mapping, like {{install: ..., installed: ~/...}}"]
    errs = []
    for k in ("install", "uninstall", "run", "version"):
        if k in link and not (isinstance(link[k], str) and link[k].strip() and "\n" not in link[k]):
            errs.append(f"{where}: link.{k} must be one command line")
    if "install" not in link:
        errs.append(f"{where}: link.install is missing: the project's own install command")
    paths = link.get("installed")
    paths = [paths] if isinstance(paths, str) else paths
    if not (isinstance(paths, list) and paths and all(isinstance(x, str) and re.match(r"^(~/|/)\S", x) for x in paths)):
        errs.append(f"{where}: link.installed must be a path (or a list of them, any one will do) that "
                    "exists once it's installed, e.g. ~/frametop")
    elif any(re.search(r"[*?[]", x) for x in paths):
        errs.append(f"{where}: link.installed: a path, not a pattern (nothing is matched against it)")
    if "readme" in link and not (isinstance(link["readme"], str) and link["readme"].startswith("https://")):
        errs.append(f"{where}: link.readme must be an https:// address")
    if "restart" in link and link["restart"] != "steamvr":
        errs.append(f"{where}: link.restart can only be steamvr (SteamVR loads it only as it starts)")
    return errs


def link_paths(link, github=None):
    """link:, its installed: always a list, and its project on GitHub (owner/name, or "")."""
    paths = link["installed"]
    return dict(link, installed=[paths] if isinstance(paths, str) else list(paths), github=github or "")


def script(c, name):
    """How to run a tweak's script (name: install, uninstall, status, run, ...), as an argument
    list: its own name.sh, or for a linked project lib/link.sh doing the same. None: it has none."""
    own = c["dir"] / f"{name}.sh"
    if own.is_file():
        return ["bash", str(own)]
    if c.get("link") and name in LINK_ACTIONS and (name not in LINK_NEEDS or c["link"].get(LINK_NEEDS[name])):
        return ["bash", str(LINK_HELPER), name, c["id"]]
    return None


def read_pack(d):
    """(info, tweak folders in order, problems)"""
    info, probs = {"name": d.name, "author": "", "api": 1, "categories": [], "order": [], "about": "", "formerly": []}, []
    if (d / "pack.md").is_file():
        try:
            data, body = manifest.front_matter((d / "pack.md").read_text())
            info.update({k: v for k, v in data.items() if k in info})
            # Its description: the text's first paragraph (headings skipped).
            paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.lstrip().startswith("#")]
            info["about"] = " ".join(paras[0].split()) if paras else ""
        except (OSError, ValueError) as e:              # (ValueError: a ManifestError, or not UTF-8)
            probs.append(f"{d.name}/pack.md: {e}")
    # (any pack's, trusted or not, is read: a wrong kind of value is a problem, and the default is used)
    if isinstance(info["formerly"], str):
        info["formerly"] = [info["formerly"]]
    for k, default in (("name", d.name), ("author", ""), ("categories", []), ("order", []), ("formerly", [])):
        v = info[k]
        ok = (isinstance(v, str) and (v or k == "author")) if isinstance(default, str) else (
            isinstance(v, list) and all(isinstance(x, str) for x in v))
        if not ok:
            probs.append(f"{d.name}/pack.md: {k} must be {'text' if isinstance(default, str) else 'a list, like [a, b]'}")
            info[k] = default
    try:
        subs = {p.name: p for p in d.iterdir() if p.is_dir() and (p / "README.md").is_file()}
    except OSError as e:
        subs = {}
        probs.append(f"{d.name}: {e}")
    order = [subs.pop(i) for i in info["order"] if i in subs] + [subs[k] for k in sorted(subs)]
    return info, order, probs


_CACHE = {}


def load(refresh=False):
    """{"components": the tweaks in use (ordered), "packs": [...], "problems": [...]}"""
    if _CACHE and not refresh:
        return _CACHE
    trust, off = trusted_packs(), off_packs()
    comps, problems, packs, cats = {}, [], [], []
    for d in pack_dirs():
        if "\n" in str(d) or "\r" in str(d):          # (trusting it would write more than its own line)
            problems.append(f"{str(d)!r}: a pack's folder can't have a line break in its name")
            continue
        info, folders, probs = read_pack(d)
        official = d in {p.resolve() for p in OFFICIAL_PACKS}
        state = ("off" if d.name in off else "official") if official else (
            ("trusted" if trust[str(d)] == pack_hash(d) else "changed") if str(d) in trust else "untrusted")
        # (label, about: shown in the user's language for an official pack; name stays the id)
        label, about = (_(info["name"]), _(info["about"])) if official else (info["name"], info["about"])
        pack = dict(dir=d, name=info["name"], label=label, author=info["author"], about=about, state=state,
                    tweaks=[f.name for f in folders])
        packs.append(pack)
        problems += probs
        if not isinstance(info["api"], int) or info["api"] > API:
            problems.append(f"{d.name}: needs a newer Frame Tweaks (pack api {info['api']}; this one knows {API})")
            continue
        cats += [c for c in info["categories"] if c not in cats]
        if state not in ("official", "trusted"):
            continue                                   # listed (./install.sh mods), not used
        for f in folders:
            c, probs = read_tweak(f)
            problems += probs
            if not c:
                continue
            c.update(pack=info["name"], pack_dir=d, official=official, replaced=None)
            if c["category"] not in cats:
                cats.append(c["category"])
            if c["id"] in comps:
                if c["replaces"]:
                    c["replaced"] = comps[c["id"]]["pack"]
                    comps[c["id"]] = c                 # (keeps its place in the order)
                else:
                    problems.append(f"{d.name}/{c['id']}: {comps[c['id']]['pack']} already has a tweak "
                                    f"{c['id']!r}; to use this one instead, add  replaces: true")
                continue
            comps[c["id"]] = c
    # formerly: a tweak's earlier ids still name it (in depends:, say), unless another tweak has one
    renamed = {}
    for i, c in comps.items():
        for old in c["formerly"]:
            if old in comps or old in renamed:
                problems.append(f"{i}: formerly: {old!r} is another tweak's id too; left out")
            else:
                renamed[old] = i
    for c in comps.values():
        c["deps"] = [renamed.get(x, x) for x in c["deps"]]
    # a tweak needing one that isn't there can't be installed
    while True:
        gone = [i for i, c in comps.items() if any(dep not in comps for dep in c["deps"])]
        if not gone:
            break
        for i in gone:
            problems.append(f"{i}: needs {', '.join(x for x in comps[i]['deps'] if x not in comps)}, which no pack has")
            del comps[i]
    rows = sorted(comps.values(), key=lambda c: cats.index(c["category"]))     # stable: pack order within
    for c in rows:                                  # (the English name: what hidden and folded groups keep)
        c["category_en"] = c["category"]
    rows = [translated(c) for c in rows]
    _CACHE.update(components=rows, packs=packs, problems=problems, renamed=renamed)
    return _CACHE


STATE = Path.home() / ".local/state/frame-tweaks"           # (install.sh's $STATE)


def apply_formerly():
    """What's kept under a tweak's former id (formerly: in its manifest) moves to its id, once:
    its install record, held, unloaded and backups entries, and hidden or shown rows; and an
    official pack turned off under a former folder name is recorded under its own. ./install.sh
    and the window run this as they start. Returns what moved."""
    moved = []
    for old, new in load(refresh=True).get("renamed", {}).items():
        for sub in ("installed", "held", "unloaded", "backups"):
            src, dst = STATE / sub / old, STATE / sub / new
            if (src.exists() or src.is_symlink()) and not (dst.exists() or dst.is_symlink()):
                src.rename(dst)
                moved.append(f"{sub}/{old} -> {new}")
        for f in (HIDDEN, SHOWN):
            ids = read_set(f)
            if old in ids:
                write_set(f, (ids - {old}) | {new})
                moved.append(f"{f.name}: {old} -> {new}")
    off = read_set(OFF_PACKS)
    if off and off_packs() != off:
        write_set(OFF_PACKS, off_packs())
        moved.append(f"{OFF_PACKS.name}: {' '.join(sorted(off))} -> {' '.join(sorted(off_packs()))}")
    if moved:
        load(refresh=True)
    return moved


def components():
    return load()["components"]


def component(cid):
    return next((c for c in components() if c["id"] == cid), None)


# Groups that were renamed: folded or hidden under the old name stays folded or hidden.
RENAMED_CATEGORIES = {"VR windows": "VR environment"}


def read_set(path):
    try:
        return {RENAMED_CATEGORIES.get(s, s) for line in path.read_text().splitlines() if (s := line.strip())}
    except OSError:
        return set()


def write_set(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{i}\n" for i in sorted(items)))


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
    for c in rows or components():
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


# ---- hidden rows: yours, plus defaults you haven't unhidden ----------------
def hidden(rows=None):
    rows = rows or components()
    defaults = {c["id"] for c in rows if "hidden-by-default" in c["flags"]}
    defaults |= {cid for cid in not_needed(rows) if not installed_record(cid)}   # (installed: its status says)
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


_CATEGORY_NAMES = {}


def category_names(rows=None):
    """{a group's name, in English or in any language Frame Tweaks has: its English name}. Hidden
    and folded groups are kept by their English name, since the window shows them in the
    keyboard's language, which can change (one folded in Spanish stayed folded only in Spanish)."""
    english = frozenset(c.get("category_en", c["category"]) for c in (rows or components()))
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
    return {names.get(s, s) for s in read_set(path)}


def set_category_hidden(category, hide):
    """category: its English name (or its name in any language Frame Tweaks has)."""
    category = category_names().get(category, category)
    cats = read_categories(HIDDEN_CATS)
    cats = cats | {category} if hide else cats - {category}
    write_set(HIDDEN_CATS, cats)


def run_label(cid):
    """The Run button's label (run: label: in the manifest), or None when there's nothing to launch."""
    c = component(cid)
    return c["run_label"] if c else None


# ---- settings ---------------------------------------------------------------------------------
# id -> {file, format ("json" | "shell": KEY=VALUE lines), about, options: [(key, title,
# [(label, value)...], default)], note}, from each tweak's settings: front matter. Only listed
# keys are written; other content is kept.
def settings_specs():
    out = {}
    for c in components():
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
    if not SHELL_NAME.fullmatch(key):     # (${!2} would run a subscript's $(...): a[$(cmd)])
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
def sudo_note(c):
    """When and why installing tweak c asks for the sudo password; "" when it won't (a Homebrew
    one, with Homebrew installed)."""
    if c.get("sudo") == "homebrew":
        return "" if BREW.exists() else _("once, if Homebrew isn't installed yet: its installer asks, to "
                                           "create /home/linuxbrew")
    return c.get("sudo") or ""


def info(cid):
    c = component(cid)
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


# ---- packs from a link (mods add | update | remove) --------------------------------------------
# A pack someone shares as a git repository (the pack at its top) is cloned into USER_PACKS. As any
# pack, nothing of it runs until it's trusted; an update fetches its newer version, which then
# waits to be trusted again; remove deletes it once its tweaks are uninstalled.
INSTALLED = Path.home() / ".local/state/frame-tweaks/installed"     # install records (./install.sh)
LINK = re.compile(r"^(https://|ssh://|git@[\w.-]+:|file://)[^\s]+$")
# (no ext:: transport, which runs a command; no submodules; never a password prompt; and none of
# the repository's own settings that run a command: hooks, an upload-pack or ssh command, an
# fsmonitor. A pack's .git/config is checked before git runs in it: pack_git_ok.)
GIT = ["git", "-c", "protocol.ext.allow=never", "-c", "submodule.recurse=false", "-c", "core.hooksPath=/dev/null",
       "-c", "core.fsmonitor=false", "-c", "core.sshCommand=ssh", "-c", "remote.origin.uploadpack=git-upload-pack",
       "-c", "remote.origin.receivepack=git-receive-pack"]
# What a clone made by `mods add` has in its .git/config. Anything else there (a filter, which git
# runs on pull, an include, a credential helper, a URL rewrite…) didn't come from Frame Tweaks, and
# trusting a pack covers its files, not its .git folder.
CLONE_CONFIG = re.compile(r"core\.(repositoryformatversion|filemode|bare|logallrefupdates|symlinks|ignorecase"
                          r"|precomposeunicode)|remote\.origin\.(url|fetch)|branch\.[^\s]+\.(remote|merge)"
                          r"|extensions\.(objectformat|refstorage)", re.IGNORECASE)


class PackError(Exception):
    """Why a pack couldn't be added, updated or removed (shown as it is)."""


def git(*args, cwd=None, check=True, timeout=120):
    """git's output; on failure PackError with git's last line (check), or None."""
    try:
        r = subprocess.run(GIT + list(args), cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true", "SSH_ASKPASS": "true"})
    except FileNotFoundError:
        raise PackError(_("git isn't installed")) from None
    except subprocess.TimeoutExpired:
        raise PackError(_("git took too long (no connection?)")) from None
    if r.returncode != 0:
        if not check:
            return None
        raise PackError((r.stderr.strip().splitlines() or [_("git {command} failed").format(command=args[0])])[-1])
    return r.stdout


def plain(text):
    """Text from a pack's repository, without control characters (it's shown in a terminal too)."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", text).strip()


def pack_folder_name(link):
    """Its folder in USER_PACKS: the repository's name (https://host/someone/my-pack.git → my-pack)."""
    name = re.sub(r"\.git$", "", link.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1])
    return re.sub(r"[^A-Za-z0-9._-]", "-", name).strip(".-") or "pack"


def pack_git_ok(d):
    """Whether a pack's .git/config holds only what a clone sets: read as a file (git config
    --file runs nothing in it)."""
    out = git("config", "--file", str(Path(d) / ".git/config"), "--name-only", "--list", check=False)
    return out is not None and all(CLONE_CONFIG.fullmatch(k.strip()) for k in out.splitlines() if k.strip())


def pack_origin(d):
    """The link a pack was added from (mods add), or None (also when its git settings aren't a
    clone's own: pack_git_ok)."""
    if not (Path(d) / ".git").is_dir() or not pack_git_ok(d):
        return None
    out = git("remote", "get-url", "origin", cwd=d, check=False)
    return plain(out) or None if out else None


def add_pack(link, ref=None):
    """Clone the pack at link (a branch or tag of it: ref) into USER_PACKS, not trusted; its folder."""
    link = link.strip()
    if not LINK.match(link):
        raise PackError(_("That isn't a link to a pack: give the address of its git repository, starting with https://"))
    if ref is not None and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", ref):
        raise PackError(_("{ref} isn't a branch or tag name").format(ref=repr(ref)))
    dest = USER_PACKS / pack_folder_name(link)
    if dest.exists():
        raise PackError(_("You have a pack in {folder} already: update it, or remove it first.").format(folder=dest))
    USER_PACKS.mkdir(parents=True, exist_ok=True)
    tmp = USER_PACKS / f".adding-{dest.name}"            # (a dot folder: not a pack while it comes in)
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        git("clone", "--quiet", *(["--branch", ref] if ref else []), "--", link, str(tmp))
        tops = [p for p in tmp.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if not (tmp / "pack.md").is_file() and not any((p / "README.md").is_file() for p in tops):
            raise PackError(_("There's no pack at the top of {link}: no pack.md, and no tweak folders (docs/mods.md).").format(
                link=link))
        tmp.rename(dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    load(refresh=True)
    return dest


def update_pack(d):
    """The newer version of a pack added from a link: {"files": changed files, "log": commit subjects}."""
    d = Path(d)
    if not (d / ".git").is_dir():
        raise PackError(_("{pack} wasn't added from a link: change its folder yourself.").format(pack=d.name))
    p = next((x for x in load(refresh=True)["packs"] if x["dir"] == d.resolve()), None)
    if p is None or p["state"] != "trusted":
        # (git runs in its folder: only in a pack you've trusted, as for looking for updates)
        raise PackError(_("{pack} isn't trusted: trust it first ({command}), or remove it and add it again.").format(
            pack=d.name, command=f'./install.sh mods trust "{d}"'))
    if (d / ".git").is_dir() and not pack_git_ok(d):
        raise PackError(_("{pack}'s git settings (.git/config) aren't the ones adding it made, and git would act "
                          "on them: remove the pack and add it again.").format(pack=d.name))
    if not pack_origin(d):
        raise PackError(_("{pack} wasn't added from a link: change its folder yourself.").format(pack=d.name))
    if git("symbolic-ref", "-q", "HEAD", cwd=d, check=False) is None:
        raise PackError(_("{pack} was added at a fixed version: to follow another one, remove it and add it again.").format(
            pack=d.name))
    old = git("rev-parse", "HEAD", cwd=d).strip()
    git("pull", "--ff-only", "--quiet", cwd=d)
    new = git("rev-parse", "HEAD", cwd=d).strip()
    load(refresh=True)
    if old == new:
        return {"files": [], "log": []}
    return {"files": [plain(x) for x in git("diff", "--name-only", old, new, cwd=d).splitlines()],
            "log": [plain(x) for x in git("log", "--format=%s", f"{old}..{new}", cwd=d).splitlines()[:20]]}


def pack_has_update(d):
    """Whether where a pack was added from has a newer version than this copy: True, False (the
    same, or one added at a fixed version), or None (couldn't look: offline, say). It only asks
    the repository for its branch's commit (git ls-remote); nothing is downloaded."""
    d = Path(d)
    if not pack_origin(d):
        return False
    branch = (git("symbolic-ref", "-q", "--short", "HEAD", cwd=d, check=False) or "").strip()
    if not branch:                                       # (a fixed version: it doesn't follow one)
        return False
    try:
        out = git("ls-remote", "--heads", "origin", f"refs/heads/{branch}", cwd=d, timeout=20)
    except PackError:
        return None
    theirs = out.split()[0] if out.split() else ""
    if not re.fullmatch(r"[0-9a-f]{40,64}", theirs):
        return None
    # (newer unless this copy already has that commit: equal, or behind work of its own)
    return git("merge-base", "--is-ancestor", theirs, "HEAD", cwd=d, check=False) is None


def packs_with_updates():
    """Your packs added from a link whose source has a newer version: their pack entries (load()).
    Only packs you trust: git reads a repository's own .git/config, which can run commands, so it
    isn't run in one you haven't trusted (nor in one changed since)."""
    return [p for p in load(refresh=True)["packs"]
            if removable(p) and p["state"] == "trusted" and pack_has_update(p["dir"])]


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
        records = {f.name: f.read_text().strip() for f in INSTALLED.iterdir() if f.is_file()}
    except OSError:
        return []
    held = STATE / "held"
    return sorted(c["id"] for c in components()
                  if c["id"] in records and records[c["id"]] != version and not c.get("link")
                  and not (held / c["id"]).exists())


def pack_installed(p):
    """A pack's tweaks that are installed (an install record), but not those another pack in use provides."""
    try:
        records = {f.name for f in INSTALLED.iterdir()}
    except OSError:
        records = set()
    used = {c["id"]: c for c in components()}
    return [t for t in p["tweaks"] if t in records and (t not in used or used[t]["pack_dir"] == p["dir"])]


def removable(p):
    """Whether a pack can be removed here: one in your packs folder (not the official ones, nor others)."""
    return p["dir"].parent == USER_PACKS.resolve()


def remove_pack(d):
    """Delete one of your packs, and its trust. Not while its tweaks are installed."""
    d = Path(d).resolve()
    p = next((x for x in load(refresh=True)["packs"] if x["dir"] == d), None)
    if p is None or not removable(p):
        raise PackError(_("Only packs in {folder} can be removed here.").format(folder=USER_PACKS))
    left = pack_installed(p)
    if left:
        ids = " ".join(left)
        raise PackError((_("Uninstall its tweaks first: {ids} ({command}).") if p["state"] == "trusted" else
                         _("Its tweaks {ids} are still installed: trust it again to uninstall them ({command}), "
                           "then remove it.")).format(ids=ids, command=f"./install.sh uninstall {ids}"))
    shutil.rmtree(d)
    set_trusted(d, False)
    load(refresh=True)


def check_folder(d):
    """(lines, bad): mods check of a pack, or of a single tweak folder."""
    single = (d / "README.md").is_file() and not (d / "pack.md").is_file() and not any(
        (p / "README.md").is_file() for p in d.iterdir() if p.is_dir() and not p.name.startswith("."))
    if single:                                     # (a pack's own README.md beside its tweaks: still a pack)
        folders, probs = [d], []
    else:                                          # (a pack: its pack.md is checked too)
        info, folders, probs = read_pack(d)
        if not isinstance(info["api"], int) or info["api"] > API:
            probs.append(f"{d.name}: needs a newer Frame Tweaks (pack api {info['api']}; this one knows {API})")
    lines, bad = list(probs), len(probs)
    for f in folders:
        c, probs = read_tweak(f)
        lines += probs
        bad += c is None
        lines.append(f"{'ok ' if c else 'BAD'} {f.name}")
    return lines, bad


def find_pack(name):
    """A pack by its folder, or by its name or folder name if only one pack goes by it (any pack
    can call itself anything: trusting the wrong one by its name mustn't be possible)."""
    packs = load()["packs"]
    found = [p for p in packs if Path(name).expanduser().resolve() == p["dir"]] or [
        p for p in packs if name in (p["name"], p["label"], p["dir"].name, str(p["dir"]))]
    if len(found) > 1:
        sys.exit(_("more than one pack is called {name}: give its folder ({folders})").format(
            name=repr(name), folders=", ".join(str(p["dir"]) for p in found)))
    if found:
        return found[0]
    sys.exit(_("no pack {name}; see {command}").format(name=repr(name), command="./install.sh mods"))


def mods(args):
    if args[:1] in (["on"], ["off"]) and len(args) == 2:
        p = find_pack(args[1])
        if p["state"] not in ("official", "off"):
            sys.exit(_("{pack} isn't one of Frame Tweaks' own packs: {command}").format(
                pack=p["name"], command="./install.sh mods trust|untrust NAME"))
        set_official(p["dir"], args[0] == "on")
        print(f"{p['name']}: " + (_("in use; its tweaks are listed") if args[0] == "on" else
                                  _("turned off (installed tweaks of it stay until you uninstall them)")))
        return
    if args[:1] in (["trust"], ["untrust"]) and len(args) == 2:
        p = find_pack(args[1])
        if p["state"] in ("official", "off"):
            sys.exit(_("{pack} comes with Frame Tweaks, so it needs no trust: {command}").format(
                pack=p["name"], command="./install.sh mods on|off NAME"))
        set_trusted(p["dir"], args[0] == "trust")
        print(f"{p['name']}: " + (_("trusted; its tweaks are listed now") if args[0] == "trust" else
                                  _("no longer used (installed tweaks of it stay until you uninstall them)")))
        return
    if args[:1] == ["check"] and len(args) == 2:
        lines, bad = check_folder(Path(args[1]).expanduser().resolve())
        print("\n".join(lines))
        sys.exit(1 if bad else 0)
    if args[:1] == ["add"] and len(args) in (2, 3):
        try:
            d = add_pack(args[1], args[2] if len(args) == 3 else None)
        except PackError as e:
            sys.exit(str(e))
        p = next(x for x in load()["packs"] if x["dir"] == d.resolve())
        print(_("Added the pack {name} in {folder}.").format(name=plain(p["name"]), folder=d)
              + (" " + _("By {author}.").format(author=plain(p["author"])) if p["author"] else ""))
        print(_("Tweaks: %s") % (", ".join(p["tweaks"]) or _("none")))
        lines, bad = check_folder(d)
        if bad:
            print(_("Problems:") + "\n  " + "\n  ".join(plain(x) for x in lines if not x.startswith("ok ")))
        print(_("It isn't used until you trust it: its tweaks would run as you. Read what they do first (each "
                "one's README.md in that folder), then: {command}").format(command=f'./install.sh mods trust "{d}"'))
        return
    if args == ["updates"]:
        found = 0
        for p in load()["packs"]:
            if not removable(p):
                continue
            if p["state"] != "trusted":         # (git runs in its folder: only in a pack you've trusted)
                if (p["dir"] / ".git").is_dir():
                    found += 1
                    print(f"{plain(p['name'])}: " + _("not checked: not trusted ({command})").format(
                        command=f'./install.sh mods trust "{p["dir"]}"'))
                continue
            if not pack_origin(p["dir"]):
                continue
            found += 1
            news = pack_has_update(p["dir"])
            print(f"{plain(p['name'])}: " + {True: _("a newer version is out: {command}").format(
                command=f'./install.sh mods update "{p["dir"]}"'), False: _("up to date"),
                None: _("couldn't check (no connection?)")}[news])
        if not found:
            print(_("No packs added from a link."))
        return
    if args[:1] in (["update"], ["remove"]) and len(args) == 2:
        p = find_pack(args[1])
        try:
            if args[0] == "remove":
                remove_pack(p["dir"])
                print(_("Removed the pack {name} ({folder}).").format(name=plain(p["name"]), folder=p["dir"]))
                return
            got = update_pack(p["dir"])
        except PackError as e:
            sys.exit(str(e))
        if not got["files"]:
            print(_("{name} is up to date.").format(name=plain(p["name"])))
            return
        print(ngettext("{name}: updated, {n} file changed.", "{name}: updated, {n} files changed.",
                       len(got["files"])).format(name=plain(p["name"]), n=len(got["files"])))
        for line in got["log"]:
            print(f"  {line}")
        print(_("It isn't used until you trust it again. Read what changed first, then: {command}").format(
            command=f'./install.sh mods trust "{p["dir"]}"'))
        return
    if args:
        sys.exit(__doc__)
    data = load()
    used = {c["id"]: c for c in data["components"]}
    for p in data["packs"]:
        state = {"official": _("official: in use"),
                 "off": _("official: turned off ({command})").format(command="./install.sh mods on NAME"),
                 "trusted": _("trusted: in use"),
                 "untrusted": _("not trusted: not used ({command})").format(command="./install.sh mods trust NAME"),
                 "changed": _("changed since you trusted it: not used until you trust it again")}[p["state"]]
        # (a pack's own text, plain: an untrusted one's name could otherwise hold terminal escapes)
        name = plain(p["name"]) if p["label"] == p["name"] else f"{plain(p['label'])} [{plain(p['name'])}]"
        print(f"{name}  ({plain(str(p['dir']))})  {state}")
        if p["about"]:
            print(f"    {plain(p['about'])}")
        if p["state"] not in ("official", "off"):
            for t in p["tweaks"]:
                c = used.get(t)
                note = "" if not c or c["pack_dir"] != p["dir"] else (
                    "  " + _("(instead of {other}'s)").format(other=c["replaced"]) if c["replaced"] else "")
                print(f"    {plain(t)}{note}")
    for pr in data["problems"]:
        print(_("problem: %s") % plain(pr))


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
    ids = {c["id"] for c in components()}
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
            groups = sorted({c["category"] for c in components()})
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
        new = load().get("renamed", {}).get(args[0])
        sys.exit(1) if not new else print(new)
    elif cmd == "apply-formerly":               # move what's kept under former ids (./install.sh registry does it too)
        print("\n".join(apply_formerly()))
    elif cmd == "known-ids" and not args:
        # (every pack's tweaks, in use or not: off, not trusted, changed; ./install.sh uninstall-self
        # tells those from tweaks no pack has any more)
        print("\n".join(sorted({t for p in load()["packs"] for t in p["tweaks"]})))
    elif cmd == "registry":                     # for ./install.sh: one line per tweak, \x1f-separated
        try:                                    # (./install.sh runs this as it starts: formerly: applies first)
            apply_formerly()
        except OSError as e:
            print(f"formerly: {e}", file=sys.stderr)
        for c in components():                  # (a line break in a summary would start a row of its own)
            print("\x1f".join(re.sub(r"[\n\r\x1f]", " ", f) for f in [c["id"], c["title"], " ".join(c["deps"]),
                                                                  c["desc"], str(c["dir"]), "1" if c["experimental"] else "",
                                                                  "1" if c["link"] else "", "1" if sudo_note(c) else ""]))
    elif cmd == "dir" and len(args) == 1:
        c = component(args[0])
        sys.exit(_("unknown component: %s") % args[0]) if not c else print(c["dir"])
    elif cmd == "link" and len(args) == 2:      # for lib/link.sh: a linked project's link: field
        c = component(args[0])
        if not c or not c["link"] or args[1] not in LINK_KEYS + ("github", "title", "app"):
            sys.exit(_("unknown component: %s") % args[0] if not c else _("%s isn't linked") % args[0])
        value = c["link"].get(args[1], "") if args[1] in LINK_KEYS + ("github",) else c[args[1]]
        print("\n".join(value) if isinstance(value, list) else value)
    elif cmd == "processes" and len(args) == 1:
        c = component(args[0])
        print("\n".join(c["processes"] if c else []))
    elif cmd == "apps":                       # tweaks that install another project's app: ID<TAB>its name
        for c in components():
            if c["app"]:
                print(f"{c['id']}\t{c['app']}")
    elif cmd == "config" and len(args) == 1:  # where it keeps its settings (~ = $HOME)
        c = component(args[0])
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
        byid, out, seen = {c["id"]: c for c in components()}, [], set()
        if args[0] not in byid:
            sys.exit(_("unknown component: %s") % args[0])
        def visit(i):                           # (as install.sh's with_deps: a cycle stops where it began)
            seen.add(i)
            for d in byid[i]["deps"]:
                if d not in seen:
                    visit(d)
                    out.append(d)
        visit(args[0])
        print(" ".join(out))
    elif cmd == "test-list":                    # dev/test-tweaks.sh's default set
        import shutil
        print(" ".join(c["id"] for c in components() if c["test"].get("offline")
                       and all(shutil.which(n) for n in c["test"].get("needs", []))))
    elif cmd == "test-keeps" and len(args) == 1:
        c = component(args[0])
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
