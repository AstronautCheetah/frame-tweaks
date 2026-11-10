#!/usr/bin/env python3
"""For translators: the official wording, in your language, of the things Frame Tweaks' text
names in other software (SteamVR's "Float in World", KDE's "System Settings", …).

  dev/i18n-terms.py LANG            write locale/glossary/LANG.terms.tsv: each phrase of SteamVR's,
                                    Steam's, KDE's and Claude Desktop's own translations that our
                                    English text uses, with its official LANG wording; refused
                                    while a source is missing (--allow-missing writes anyway)
  dev/i18n-terms.py LANG --check    our LANG.po translations that don't use that wording
  dev/i18n-terms.py LANG --lookup WORD…
                                    how those programs translate a word or phrase (for the
                                    glossary's own terms: "Dashboard", "Passthrough", …)

It reads the translations those programs install (SteamVR, Steam, Claude Desktop, Qt, KDE: a
Steam Frame has all of them; a source that isn't on this machine is skipped, and said so, and the
.tsv isn't rewritten without it: its rows would silently go), and Android's Settings app's (the
phone side of Android Mirror), downloaded once from the Android source into
~/.cache/frame-tweaks/i18n-terms. Use it before a translation pass: the terms go with the glossary
(locale/BATCH.md)."""
import collections
import gettext
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import i18n  # noqa: E402

HOME = Path.home()
STEAMVR = Path("/opt/steamvr/resources/webinterface/dashboard/localization")
STEAMUI = HOME / ".local/share/Steam/steamui/localization"
KDE = Path("/usr/share/locale")
CLAUDE = HOME / ".local/opt/claude-desktop/resources"
# Claude Desktop's texts: loose JSON files up to 4.22 (looked at first, should a later version
# go back to them), inside its Electron archives since 4.23 (app.asar: the window's, under
# resources/i18n; ion-dist.asar: the chat's, under i18n and i18n/dynamic).
CLAUDE_LOOSE = [CLAUDE, CLAUDE / "i18n", CLAUDE / "ion-dist/i18n"]
CLAUDE_ASARS = [CLAUDE / "app.asar", CLAUDE / "ion-dist.asar"]
# Our language code → Valve's name for it (Steam, SteamVR) and Claude's file name.
VALVE = {"es_419": "latam", "es": "spanish", "pt_BR": "brazilian", "pt": "portuguese", "de": "german",
         "fr": "french", "it": "italian", "ru": "russian", "pl": "polish", "ja": "japanese", "ko": "koreana",
         "zh_CN": "schinese", "zh_TW": "tchinese", "nl": "dutch", "sv": "swedish", "da": "danish",
         "fi": "finnish", "nb": "norwegian", "cs": "czech", "hu": "hungarian", "ro": "romanian", "tr": "turkish",
         "uk": "ukrainian", "bg": "bulgarian", "el": "greek", "th": "thai", "vi": "vietnamese"}
AOSP = "https://raw.githubusercontent.com/aosp-mirror/"
ANDROID_FILES = ["platform_frameworks_base/main/packages/SettingsLib/res/{}/strings.xml",
                 "platform_packages_apps_settings/main/res/{}/strings.xml",
                 "platform_packages_apps_settings/main/res-product/{}/strings.xml"]
CACHE = HOME / ".cache/frame-tweaks/i18n-terms"
QT = Path("/usr/share/qt6/translations")
LCONVERT = Path("/usr/lib/qt6/bin/lconvert")
SOURCES = ("SteamVR", "Steam", "Android", "Claude Desktop", "Qt", "KDE")      # (the first one wins a disagreement)


def clean(text):
    """A UI text as people read it: KDE's & accelerators and trailing … / : taken off."""
    text = re.sub(r"&(?=\w)", "", text).strip()
    return re.sub(r"(\.\.\.|…|:)$", "", text).strip()


def steamvr(lang):
    v = VALVE.get(lang) or VALVE.get(lang.split("_")[0])
    for en in sorted(STEAMVR.glob("*_english.json")) if v else []:
        tr = en.with_name(en.name.replace("_english", f"_{v}"))
        if tr.exists():
            a, b = json.loads(en.read_text()), json.loads(tr.read_text())
            yield from ((a[k], b[k]) for k in a if isinstance(a[k], str) and isinstance(b.get(k), str))


def steam_js(path):
    """Steam's UI strings: a JSON.parse(`…`) inside a webpack chunk."""
    m = re.search(r"JSON\.parse\(`(.*)`\)", path.read_text(encoding="utf-8", errors="replace"), re.S)
    if not m:
        return {}
    simple = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}

    def unescape(e):                                  # (a template literal's escapes; then it's JSON)
        c = e[1]
        if c[0] in "xu" and len(c) > 1:
            return chr(int(c[1:].strip("{}"), 16))
        return simple.get(c, c)
    body = re.sub(r"\\(x[0-9A-Fa-f]{2}|u\{[0-9A-Fa-f]+\}|u[0-9A-Fa-f]{4}|.)", unescape, m[1], flags=re.S)
    try:
        return json.loads(body)
    except ValueError:
        return {}


def steam(lang):
    v = VALVE.get(lang) or VALVE.get(lang.split("_")[0])
    for en in sorted(STEAMUI.glob("*_english-json.js")) if v else []:
        tr = en.with_name(en.name.replace("_english", f"_{v}"))
        if tr.exists():
            a, b = steam_js(en), steam_js(tr)
            yield from ((a[k], b[k]) for k in a if isinstance(a[k], str) and isinstance(b.get(k), str))


def android_strings(folder):
    """{key: text} of one Android strings.xml folder (values, values-es-rUS, …), cached."""
    import urllib.request
    import xml.etree.ElementTree as ET
    out = {}
    for f in ANDROID_FILES:
        path = CACHE / f.format(folder).replace("/", "_")
        if not path.exists():
            try:
                with urllib.request.urlopen(AOSP + f.format(folder), timeout=30) as r:
                    data = r.read()
            except OSError:
                continue
            CACHE.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        try:
            root = ET.fromstring(path.read_bytes())
        except ET.ParseError:
            continue
        for el in root.iter("string"):
            text = "".join(el.itertext()).strip().strip('"').replace("\\'", "'")
            text = text.replace("\\u2011", "-").replace("\u2011", "-")            # (Android's Wi‑Fi)
            if el.get("name") and text:
                out[(el.get("name"), el.get("product"))] = text
    return out


def android(lang):
    base, _sep, region = lang.partition("_")
    folder = {"es_419": "values-es-rUS", "zh_CN": "values-zh-rCN", "zh_TW": "values-zh-rTW", "nb": "values-nb",
              "nl_BE": "values-nl"}.get(          # (no Belgian Dutch of its own: Dutch)
        lang, f"values-{base}-r{region}" if region else f"values-{base}")
    a, b = android_strings("values"), android_strings(folder)
    yield from ((a[k], b[k]) for k in a if k in b)


def asar(path):
    """{"folder/name": (offset, size)} of the files inside an Electron archive (app.asar), offsets
    into the archive. Its layout, checked against Claude Desktop 4.23118.0's: four little-endian
    u32 (4; the header's size, after which, from byte 8, the files' bytes follow end to end; the
    index's size padded to 4 plus 4; the index's size), the JSON index {"files": {name: {"files":
    …} | {"offset": "n", "size": n}}} with offsets counted from the files' start, and the files.
    An entry marked "unpacked" (a native library) is beside the archive, not in it: left out."""
    with open(path, "rb") as f:
        _four, header_size, _padded, index_size = struct.unpack("<4I", f.read(16))
        index = json.loads(f.read(index_size))
    base, out = 8 + header_size, {}

    def walk(folder, prefix):
        for name, entry in folder.get("files", {}).items():
            if "files" in entry:
                walk(entry, f"{prefix}{name}/")
            elif "offset" in entry and not entry.get("unpacked"):
                out[prefix + name] = (base + int(entry["offset"]), int(entry["size"]))
    walk(index, "")
    return out


def asar_json(f, entry):
    """One JSON file of an open archive, by its asar() entry."""
    offset, size = entry
    f.seek(offset)
    return json.loads(f.read(size))


def claude_file(want, names):
    """The language's file among a folder's names: es-419.json for es_419, fr-FR.json for fr,
    nl.json for nl_BE (Claude has no Belgian Dutch, as Android hasn't)."""
    base = want.split("-")[0]
    regional = sorted(n for n in names if n.startswith(f"{base}-") and n.endswith(".json"))
    return next((n for n in (f"{want}.json", *regional, f"{base}.json") if n in names), None)


def claude(lang):
    """Claude Desktop's texts: every folder, loose or in an archive, with an en-US.json and the
    language's (keys are hashes of the English, the same in every language's file)."""
    want = lang.replace("_", "-")

    def pairs(a, b):
        return ((a[k], b[k]) for k in a if isinstance(a[k], str) and isinstance(b.get(k), str))
    for d in CLAUDE_LOOSE:
        names = {f.name for f in d.glob("*.json")} if d.is_dir() else set()
        tr = claude_file(want, names)
        if "en-US.json" in names and tr:
            yield from pairs(json.loads((d / "en-US.json").read_text()), json.loads((d / tr).read_text()))
    for archive in CLAUDE_ASARS:
        if not archive.exists():
            continue
        files = asar(archive)
        folders = collections.defaultdict(set)
        for p in files:
            folder, _sep, name = p.rpartition("/")
            folders[folder].add(name)
        with open(archive, "rb") as f:
            for folder, names in sorted(folders.items()):
                tr = claude_file(want, names)
                if "en-US.json" in names and tr:
                    a, b = (asar_json(f, files[f"{folder}/{n}"]) for n in ("en-US.json", tr))
                    yield from pairs(a, b)


def qt(lang):
    """Qt's own translations (key names, standard dialogs): its .qm files, read through lconvert."""
    import subprocess
    if not LCONVERT.exists():
        return
    for code in dict.fromkeys([lang, lang.split("_")[0]]):
        for qm in sorted(QT.glob(f"*_{code}.qm")):
            r = subprocess.run([str(LCONVERT), "-i", str(qm), "-of", "po", "-o", "-"], capture_output=True, text=True)
            for (_ctx, msgid), strs in i18n.parse_po(r.stdout).items():
                if strs[0]:
                    yield msgid, strs[0]


def kde(lang):
    for code in dict.fromkeys([lang, lang.split("_")[0]]):
        for mo in sorted((KDE / code / "LC_MESSAGES").glob("*.mo")):
            try:
                with open(mo, "rb") as f:
                    cat = gettext.GNUTranslations(f)._catalog
            except (OSError, ValueError):            # (an unreadable or odd catalogue: skipped)
                continue
            for k, v in cat.items():
                if isinstance(k, str) and k and isinstance(v, str) and v:
                    yield k.split("\x04")[-1], v


def official(lang):
    """{English phrase: [(translation, source, count)]}, the most used translation first, and
    {source: how many texts it gave} (0: not on this machine)."""
    found, here = collections.defaultdict(collections.Counter), {}
    for name, source in zip(SOURCES, (steamvr, steam, android, claude, qt, kde)):
        here[name] = 0
        for en, tr in source(lang):
            en, tr = clean(en), clean(tr)
            if en and tr and en != tr and "\n" not in en and len(en) <= 60 and not re.search(r"[{}%<$]", en):
                found[en][(tr, name)] += 1
                here[name] += 1
    rank = {s: i for i, s in enumerate(SOURCES)}
    out = {en: sorted(((tr, src, c) for (tr, src), c in counts.items()), key=lambda t: (rank[t[1]], -t[2]))
           for en, counts in found.items()}
    return out, here


def summary(here):
    return "; ".join(f"{name}: {n} texts" if n else f"{name}: not on this machine" for name, n in here.items())


def lowered(table):
    """{phrase lower-cased: [its spellings in table]}: 'Apply changes' finds KDE's 'Apply Changes'."""
    out = {}
    for en in table:
        out.setdefault(en.lower(), []).append(en)
    return out


def same(text):
    """A wording for comparison: a no-break space (KDE's and Android's French and Spanish, U+00A0
    or the narrow U+202F) counts as the plain space our .po may use."""
    return text.replace("\u00a0", " ").replace("\u202f", " ")


SMALL = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with"}


def phrases(msgid):
    """What a text of ours names in other software: the whole text if it's a short label of two
    words or more ("Apply changes"), a quoted or bold one ("Change Password", **Lock now**), or a
    Title Case run of words ("Float in World", "System Settings")."""
    out = set()
    whole = clean(msgid)
    if len(whole) <= 60 and len(whole.split()) >= 2:
        out.add(whole)
    for q in re.findall(r'"([^"\n]{3,60})"|“([^”\n]{3,60})”|\*\*([^*\n]{3,60})\*\*|<b>([^<\n]{3,60})</b>', msgid):
        name = clean(next(x for x in q if x))
        if name[:1].isupper():                        # (a name; not an emphasised word: <b>removed</b>)
            out.add(name)
    words = re.findall(r"[\w'’+-]+|[^\w\s]", re.sub(r"<[^>]+>|`[^`]*`|\{[^}]*\}|%\w", " , ", msgid))
    for n in range(2, 7):
        for i in range(len(words) - n + 1):
            run = words[i:i + n]
            if (all(re.match(r"\w", w) for w in run) and run[0][:1].isupper() and run[-1][:1].isupper()
                    and all(w[:1].isupper() or w in SMALL for w in run)):
                out.add(" ".join(run))
    return out


def template_msgids():
    """Every English text in locale/frame-tweaks.pot."""
    out = []
    for block in re.split(r"\n\s*\n", (ROOT / "locale/frame-tweaks.pot").read_text()):
        m = re.search(r'^msgid ((?:".*"\n?)+)', block, re.M)
        text = "".join(i18n.unquote(q) for q in re.findall(r'".*"', m[1])) if m else ""
        if text:
            out.append(text)
    return out


def terms(lang):
    """[(English, official, source, alternatives, our texts using it)]"""
    table, here = official(lang)
    lower = lowered(table)
    rank = {s: i for i, s in enumerate(SOURCES)}
    used, spelling = collections.defaultdict(list), {}
    for msgid in template_msgids():
        for p in phrases(msgid):
            key = clean(p).lower()                    # (as --lookup matches: KDE's 'Apply Changes' is ours)
            if key in lower:
                used[key].append(msgid)
                spelling.setdefault(key, p)
    rows = []
    for key in sorted(used):
        hits = sorted((h for en in lower[key] for h in table[en]), key=lambda t: (rank[t[1]], -t[2]))
        (tr, src, _n), *rest = hits
        alts, seen = [], set()
        for t, s, _c in rest:                         # (one per wording and source; the official's own
            if same(t) != same(tr) and (same(t), s) not in seen:      # wording with other spaces: no lookalike)
                seen.add((same(t), s))
                alts.append(f"{t} ({s})")
        rows.append((spelling[key], tr, src, "; ".join(alts), used[key]))
    return rows, here


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        sys.exit(__doc__)
    lang = sys.argv[1]
    if "--lookup" in sys.argv:
        table, here = official(lang)
        print(summary(here))
        lower = lowered(table)
        for word in sys.argv[sys.argv.index("--lookup") + 1:]:
            hits = [h for en in lower.get(clean(word).lower(), []) for h in table[en]]
            print(f"{word}: " + ("; ".join(dict.fromkeys(f"{t} ({s}, {c}×)" for t, s, c in hits)) or "not found"))
        return
    rows, here = terms(lang)
    print(summary(here))
    if "--check" in sys.argv:
        po = ROOT / "locale" / f"{lang}.po"
        done = i18n.parse_po(po.read_text()) if po.exists() else {}
        n = 0
        for en, tr, src, _alts, msgids in rows:
            for m in msgids:
                ours = (done.get((None, m)) or [""])[0]
                if ours and same(tr).lower() not in same(ours).lower() and en.lower() not in {"ok"}:
                    print(f"{src} says {en!r} is {tr!r}; ours: {m[:60]!r} → {ours[:70]!r}")
                    n += 1
        print(f"{n} to look at")
        return
    missing = [name for name, n in here.items() if not n]
    if missing and "--allow-missing" not in sys.argv:
        # (rewriting without a source would drop its rows, and a glossary row that vanishes
        # reads as "no official wording"; on a Frame every source is there)
        sys.exit(f"not written: {', '.join(missing)} missing on this machine (--allow-missing writes anyway)")
    out = ROOT / "locale/glossary" / f"{lang}.terms.tsv"
    out.parent.mkdir(exist_ok=True)
    lines = [f"# Official {lang} wording of what Frame Tweaks names in other software, from their own",
             "# translations (dev/i18n-terms.py; don't edit by hand). Columns: English, official,",
             "# source, other wordings seen, how many of our texts use it.",
             "English\tofficial\tsource\talternatives\tused"]
    lines += [f"{en}\t{tr}\t{src}\t{alts}\t{len(m)}" for en, tr, src, alts, m in rows]
    out.write_text("\n".join(lines) + "\n")
    print(f"{out.relative_to(ROOT)}: {len(rows)} terms")


if __name__ == "__main__":
    main()
