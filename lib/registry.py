"""The packs and their tweaks, as lib/sft.py (the installer window and ./install.sh) uses them:
where packs are, which ones are in use (official, turned off, trusted), each tweak's manifest
checked and read (docs/mods.md), and the tweak list load() makes of them.

Imported through lib/sft.py, which hands every name here on: the code here and in
lib/userpacks.py looks these up as registry.NAME when it runs, so a test patches them here.
"""
import hashlib
import os
import re
from pathlib import Path

import manifest  # (lib/ is on the path: lib/sft.py put it there)
import i18n
from i18n import _

REPO = Path(__file__).resolve().parent.parent

CONF = Path.home() / ".config/frame-tweaks/installer"      # (before 0.5: ~/.config/steam-frame-tweaks)
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
            "app", "link", "sudo", "formerly", "when_not_needed", "hardware", "fail_safe")
# hardware: what part of the Frame's hardware the tweak drives (a charger switch, a fan, a
# display setting). Such a tweak must also be experimental and say, in fail_safe, what it does
# by itself when things go wrong: a tweak that drove the charger's pause switch was on a Frame
# that stopped charging, and these can cost someone a device (docs/DESIGN.md, "Hardware").
# app: the name of the other project's app the tweak installs (Claude Desktop, Full Keyboard, …).
# Uninstalling Frame Tweaks leaves those tweaks, and so their apps, unless asked to remove them.
# config: where a tweak keeps its settings (files or folders; its settings.file counts too). An
# uninstall keeps them, or removes them when the Preferences say so (lib/sft.py UNINSTALL_PREF). Only below
# these roots: data kept elsewhere (adb's pairing keys, the dictation history, ~/.claude) stays.
CONFIG_ROOTS = ("~/.config/", "~/.var/app/", "~/.local/state/frame-tweaks/")
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
                    for chunk in iter(lambda f=f: f.read(1 << 20), b""):
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
                and isinstance(a.get("when", ""), str) and isinstance(a.get("about", ""), str)
                and isinstance(a.get("keys", []), list)):
            errs.append(f"{where}: each settings action needs a label and a script in the tweak's folder "
                        "(args, when, about, keys optional)")
        elif any(k not in {o.get("key") for o in opts if isinstance(o, dict)} for k in a.get("keys", [])):
            errs.append(f"{where}: {a['label']}: keys: only this tweak's own options (what the action applies)")
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
    if "when_not_needed" in data and data["when_not_needed"] != "uninstall":
        errs.append(f"{where}: when_not_needed takes uninstall (remove the tweak once this Frame doesn't need it)")
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
    for k in ("hardware", "fail_safe"):
        if not isinstance(data.get(k) or "", str):
            errs.append(f"{where}: {k} must be text")
    if data.get("hardware"):
        if not data.get("experimental"):
            errs.append(f"{where}: a tweak with hardware: must be experimental too (and say why it's safe to try)")
        if not data.get("fail_safe"):
            errs.append(f"{where}: a tweak with hardware: needs fail_safe: what it does by itself when "
                        "something goes wrong (stops, puts the hardware back as it was)")
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
        experimental=data.get("experimental") or "", hardware=data.get("hardware") or "",
        fail_safe=data.get("fail_safe") or "", icon=icon, sudo=(data.get("sudo") or "").strip(), formerly=formerly,
        run_label=run.get("label", "Run") if (d / "run.sh").is_file() or (link or {}).get("run") else None,
        link=link_paths(link, github_repo(src.get("url"), link.get("readme"))) if link else None,
        processes=procs, settings=data.get("settings"),
        app=data.get("app") or "",
        config=list(dict.fromkeys(conf + ([data["settings"]["file"]] if data.get("settings") else []))),
        known_issue=data.get("known_issue"), wallet_apps=apps,
        upstream_readme=data.get("upstream_readme", ""),
        when_not_needed=data.get("when_not_needed") or "",     # ("uninstall": ./install.sh tidy removes it then)
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
                    "exists once it's installed, e.g. ~/my-app/bin/my-app")
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
