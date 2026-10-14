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
  sft.py mods check FOLDER              check a pack or a single tweak folder, using nothing
  sft.py hide|unhide ID...              hide a row in the installer window (or show it again)
  sft.py hide-group|unhide-group NAME   the same for a whole group (e.g. "VR environment")
  sft.py info ID                        what the installer window's details page shows
  sft.py run-label ID                   the Run button's label (nothing if the tweak has none)
  sft.py settings ID                    current settings, and what each can be set to
  sft.py settings ID KEY=VALUE...       change them (VALUE: a listed value or its label)
  sft.py settings ID --reset            back to the defaults
For ./install.sh and dev/test-tweaks.sh: registry, dir ID, deps ID, processes ID, test-list,
test-keeps ID.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manifest  # noqa: E402
import i18n  # noqa: E402
from i18n import _  # noqa: E402

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
CONF = Path.home() / ".config/frame-tweaks/installer"      # (before 0.5: ~/.config/steam-frame-tweaks)
HIDDEN, SHOWN = CONF / "hidden", CONF / "shown"     # SHOWN: default-hidden rows you unhid
COLLAPSED, HIDDEN_CATS = CONF / "collapsed-categories", CONF / "hidden-categories"
TRUSTED = CONF / "trusted-packs"                    # "<folder>\t<sha256 of its files>" per line

# ---- packs and tweaks -------------------------------------------------------------------------
# A pack is a folder of tweak folders, with an optional pack.md; a tweak is a folder whose
# README.md starts with front matter (docs/mods.md). The official pack is loaded like any other;
# a user's packs need trusting first (they run as you), and a tweak of theirs may take the place
# of one with the same id only by saying `replaces: true`.
OFFICIAL = REPO / "packs/official"
OFFICIAL_PACKS = [OFFICIAL]                 # (dev/i18n.py: the packs whose text is in the template)
USER_PACKS = Path.home() / ".local/share/frame-tweaks/packs"
API = 1                                             # the newest pack api this version knows
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TEXT = ("title", "emoji", "category", "tier", "summary", "what", "why", "author",
        "changes", "access", "survives_updates", "undo")
OPTIONAL = ("source", "depends", "hidden_by_default", "experimental", "icon", "run", "processes",
            "settings", "known_issue", "wallet_apps", "test", "replaces", "upstream_readme")
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
    """The official pack, then other folders in this checkout's packs/ (local, not published:
    e.g. packs/attic for tweaks set aside), then ~/.local/share/frame-tweaks/packs/*, then
    FRAME_TWEAKS_PACKS (folders separated by :, each a pack). All but the official one need trust."""
    out = [OFFICIAL]
    out += sorted(d for d in OFFICIAL.parent.iterdir() if d.is_dir() and d != OFFICIAL and not d.name.startswith("."))
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
    """sha256 over a pack's files (names and contents): trust is for this content only."""
    h = hashlib.sha256()
    for f in sorted(p for p in Path(d).rglob("*") if p.is_file() and not any(
            part in (".git", "__pycache__") for part in p.relative_to(d).parts)):
        h.update(str(f.relative_to(d)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def trusted_packs():
    out = {}
    try:
        for line in TRUSTED.read_text().splitlines():
            path, _, digest = line.partition("\t")
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


def check_settings(st, cid, where):
    errs = []
    if not isinstance(st, dict):
        return [f"{where}: settings must be a mapping"]
    f = st.get("file")
    if not (isinstance(f, str) and f.startswith("~/.config/")):
        errs.append(f"{where}: settings.file must be a file under ~/.config/")
    if st.get("format") not in ("json", "shell"):
        errs.append(f"{where}: settings.format must be json or shell")
    opts = st.get("options")
    if not isinstance(opts, list) or not opts:
        return errs + [f"{where}: settings.options must be a list"]
    for o in opts:
        if not (isinstance(o, dict) and isinstance(o.get("key"), str) and isinstance(o.get("title"), str)
                and isinstance(o.get("choices"), list) and o["choices"]):
            errs.append(f"{where}: each settings option needs key, title, default and choices")
            continue
        vals = []
        for c in o["choices"]:
            if not (isinstance(c, dict) and isinstance(c.get("label"), str) and "value" in c):
                errs.append(f"{where}: {o['key']}: each choice needs a label and a value")
            else:
                vals.append(c["value"])
        if o.get("default") not in vals:
            errs.append(f"{where}: {o['key']}: the default must be one of the choices' values")
    for o in opts:
        if isinstance(o, dict) and o.get("checkbox") and len(o.get("choices") or []) != 2:
            errs.append(f"{where}: {o.get('key')}: a checkbox option needs exactly two choices (on, then off)")
    if not (isinstance(st.get("include", []), list) and all(isinstance(i, str) for i in st.get("include", []))):
        errs.append(f"{where}: settings.include must be a list of tweak ids")
    for a in st.get("actions", []):
        if not (isinstance(a, dict) and isinstance(a.get("label"), str) and isinstance(a.get("script"), str)
                and isinstance(a.get("args", []), list) and isinstance(a.get("when", ""), str)):
            errs.append(f"{where}: each settings action needs a label and a script (args, when, about optional)")
    return errs


def read_tweak(d):
    """(component dict, [problems]) for a tweak folder; None as the dict if it can't be used."""
    cid, where = d.name, f"{d.parent.name}/{d.name}"
    if not ID.match(cid):
        return None, [f"{where}: a tweak's folder name (its id) must be lower-case letters, digits and -"]
    try:
        data, _ = manifest.front_matter((d / "README.md").read_text())
    except (OSError, manifest.ManifestError) as e:
        return None, [f"{where}/README.md: {e}"]
    errs = [f"{where}: {k} is missing (or not text)" for k in TEXT if not isinstance(data.get(k), str) or not data[k]]
    warn = [f"warning: {where}: unknown key {k!r} (ignored)" for k in data if k not in TEXT + OPTIONAL]
    if data.get("tier") not in (None, "core", "extras", "helper"):
        errs.append(f"{where}: tier must be core, extras or helper")
    deps = data.get("depends", [])
    if not (isinstance(deps, list) and all(isinstance(x, str) for x in deps)):
        errs.append(f"{where}: depends must be a list of tweak ids")
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
    if not (isinstance(icon, dict) and set(icon) <= {"file", "flatpak", "theme"}):
        errs.append(f"{where}: icon takes file, flatpak and theme")
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
        experimental=data.get("experimental", ""), icon=icon,
        run_label=run.get("label", "Run") if (d / "run.sh").is_file() else None,
        processes=data.get("processes", []), settings=data.get("settings"),
        known_issue=data.get("known_issue"), wallet_apps=data.get("wallet_apps", []),
        upstream_readme=data.get("upstream_readme", ""),
        test=data.get("test", {}), replaces=data.get("replaces", False),
        changes=data["changes"], access=data["access"], survives_updates=data["survives_updates"],
        undo=data["undo"]), warn


def read_pack(d):
    """(info, tweak folders in order, problems)"""
    info, probs = {"name": d.name, "author": "", "api": 1, "categories": [], "order": [], "about": ""}, []
    if (d / "pack.md").is_file():
        try:
            data, body = manifest.front_matter((d / "pack.md").read_text())
            info.update({k: v for k, v in data.items() if k in info})
            # Its description: the text's first paragraph (headings skipped).
            paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.lstrip().startswith("#")]
            info["about"] = " ".join(paras[0].split()) if paras else ""
        except manifest.ManifestError as e:
            probs.append(f"{d.name}/pack.md: {e}")
    subs = {p.name: p for p in d.iterdir() if p.is_dir() and (p / "README.md").is_file()}
    order = [subs.pop(i) for i in info["order"] if i in subs] + [subs[k] for k in sorted(subs)]
    return info, order, probs


_CACHE = {}


def load(refresh=False):
    """{"components": the tweaks in use (ordered), "packs": [...], "problems": [...]}"""
    if _CACHE and not refresh:
        return _CACHE
    trust = trusted_packs()
    comps, problems, packs, cats = {}, [], [], []
    for d in pack_dirs():
        info, folders, probs = read_pack(d)
        official = d == OFFICIAL.resolve()
        state = "official" if official else "trusted" if trust.get(str(d)) == pack_hash(d) else (
            "changed" if str(d) in trust else "untrusted")
        pack = dict(dir=d, name=info["name"], author=info["author"], about=info["about"], state=state,
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
    # a tweak needing one that isn't there can't be installed
    while True:
        gone = [i for i, c in comps.items() if any(dep not in comps for dep in c["deps"])]
        if not gone:
            break
        for i in gone:
            problems.append(f"{i}: needs {', '.join(x for x in comps[i]['deps'] if x not in comps)}, which no pack has")
            del comps[i]
    rows = sorted(comps.values(), key=lambda c: cats.index(c["category"]))     # stable: pack order within
    rows = [translated(c) for c in rows]
    _CACHE.update(components=rows, packs=packs, problems=problems)
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
    try:   # a shell file: sourced, as the scripts do (values may be shell-quoted)
        return subprocess.run(["bash", "-c", f'. "$1" 2>/dev/null; printf %s "${{{key}:-}}"', "_", str(s["file"])],
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
    c = component(cid)
    if not c:
        sys.exit(f"unknown component: {cid}")
    lines = [f"{c['title']}  ({c['category']})", "", c["what"]]
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
    if not c["official"]:
        lines += [f"From the pack {c['pack']!r} ({c['pack_dir']}), not part of Frame Tweaks"
                  + (f"; used instead of {c['replaced']}'s" if c["replaced"] else "")]
    lines += ["More: " + str(c["readme"])]
    label = run_label(cid)
    if label:
        lines += [f"Run ({label}): ./install.sh run {cid}"]
    if cid in SETTINGS:
        lines += [f"Settings: ./install.sh settings {cid}"]
    return "\n".join(lines)


def find_pack(name):
    """A pack by its name, folder name or folder."""
    for p in load()["packs"]:
        if name in (p["name"], p["dir"].name, str(p["dir"])) or Path(name).expanduser().resolve() == p["dir"]:
            return p
    sys.exit(f"no pack {name!r}; see ./install.sh mods")


def mods(args):
    if args[:1] in (["trust"], ["untrust"]) and len(args) == 2:
        p = find_pack(args[1])
        if p["state"] == "official":
            sys.exit("the official pack is always used")
        set_trusted(p["dir"], args[0] == "trust")
        print(f"{p['name']}: " + ("trusted; its tweaks are listed now" if args[0] == "trust" else
                                  "no longer used (installed tweaks of it stay until you uninstall them)"))
        return
    if args[:1] == ["check"] and len(args) == 2:
        d = Path(args[1]).expanduser().resolve()
        folders = [d] if (d / "README.md").is_file() and not (d / "pack.md").is_file() else read_pack(d)[1]
        bad = 0
        for f in folders:
            c, probs = read_tweak(f)
            for pr in probs:
                print(pr)
            bad += c is None
            print(f"{'ok ' if c else 'BAD'} {f.name}")
        sys.exit(1 if bad else 0)
    if args:
        sys.exit(__doc__)
    data = load()
    used = {c["id"]: c for c in data["components"]}
    for p in data["packs"]:
        state = {"official": "official", "trusted": "trusted: in use",
                 "untrusted": "not trusted: not used (./install.sh mods trust NAME)",
                 "changed": "changed since you trusted it: not used until you trust it again"}[p["state"]]
        print(f"{p['name']}  ({p['dir']})  {state}")
        if p["about"]:
            print(f"    {p['about']}")
        if p["state"] != "official":
            for t in p["tweaks"]:
                c = used.get(t)
                note = "" if not c or c["pack_dir"] != p["dir"] else (
                    f"  (instead of {c['replaced']}'s)" if c["replaced"] else "")
                print(f"    {t}{note}")
    for pr in data["problems"]:
        print("problem: " + pr)


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
    elif cmd == "mods":
        mods(args)
    elif cmd == "registry":                     # for ./install.sh: one line per tweak, \x1f-separated
        for c in components():
            print("\x1f".join([c["id"], c["title"], " ".join(c["deps"]), c["desc"], str(c["dir"]),
                               "1" if c["experimental"] else ""]))
    elif cmd == "dir" and len(args) == 1:
        c = component(args[0])
        sys.exit(f"unknown component: {args[0]}") if not c else print(c["dir"])
    elif cmd == "processes" and len(args) == 1:
        c = component(args[0])
        print("\n".join(c["processes"] if c else []))
    elif cmd == "deps" and len(args) == 1:      # what ID needs, transitively, dependencies first
        byid, out = {c["id"]: c for c in components()}, []
        def visit(i):
            for d in byid[i]["deps"]:
                if d not in out:
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
