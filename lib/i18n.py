"""Translations: GNU gettext's message catalogues (.po files in locale/), read directly.

Translators edit locale/<language>.po (e.g. de.po, pt_BR.po) made from the template
locale/frame-tweaks.pot (dev/i18n.py makes and updates both; see locale/README.md). Code marks
text with _("..."), ngettext(singular, plural, n) or pgettext(context, "..."); text without a
translation stays English. The language, best first: FRAME_TWEAKS_LANGUAGE (to choose one; "en": English), the
active keyboard's language (Steam's VR keyboard in the VR session, KDE's layout in desktop mode;
an English one says nothing), then the usual LANGUAGE, LC_ALL, LC_MESSAGES or LANG. A language
without its own file uses one for the same language elsewhere (es, es_MX → es_419.po).

Shell scripts: lib/i18n.sh (t 'Text with %s' ARGS), which reads `python3 i18n.py bash`.
Installed programs use a copy in ~/.local/share/frame-tweaks/i18n (lib/common.sh install_i18n).

No compile step and no dependency: the .po files are read as they are (fuzzy entries skipped)."""
import ast
import gettext
import glob
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCALE = HERE / "locale" if (HERE / "locale").is_dir() else HERE.parent / "locale"     # (installed copy, or the repo)


def unquote(s):
    """A .po string literal ("...", C escapes) as text."""
    return ast.literal_eval(s)


def parse_po(text):
    """{(context, msgid): [msgstr, ...]} from a .po file's text: msgstr is a one-item list, or one
    per plural form (msgstr[n]). Fuzzy and untranslated entries are left out."""
    out, entry, field, fuzzy = {}, {}, None, False

    def flush():
        nonlocal entry, fuzzy
        if "msgid" in entry and entry["msgid"] and not fuzzy:
            strs = [entry[k] for k in sorted(k for k in entry if k.startswith("msgstr"))]
            if any(strs):
                out[(entry.get("msgctxt"), entry["msgid"])] = strs
        entry, fuzzy = {}, False

    for line in text.splitlines():
        line = line.strip()
        if not line:
            flush()
            field = None
        elif line.startswith("#,"):
            if entry:
                flush()
            fuzzy = "fuzzy" in line
        elif line.startswith("#"):
            continue
        elif line.startswith('"') and field:
            entry[field] += unquote(line)
        else:
            m = re.match(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[(\d+)\])?)\s+(".*")$', line)
            if not m:
                continue
            key = m[1] if not m[2] else f"msgstr[{int(m[2]):03d}]"
            if key in ("msgctxt", "msgid") and "msgid" in entry and any(k.startswith("msgstr") for k in entry):
                flush()
            field = "msgstr" if key == "msgstr" else key
            entry[field] = unquote(m[3])
    flush()
    return out


def plural_index(n, header):
    """The plural form for n, from the catalogue's Plural-Forms header (gettext's own parser)."""
    m = re.search(r"plural\s*=\s*([^;]+)", header or "")
    try:
        return gettext.c2py(m[1])(n) if m else (0 if n == 1 else 1)
    except (ValueError, TypeError):
        return 0 if n == 1 else 1


# ---- the active keyboard's language ------------------------------------------------------------
CHECK_EVERY = 5.0                    # seconds: at most one look at the keyboard per this
STEAM_CONFIG = Path.home() / ".local/share/Steam/config/config.vdf"
STEAM_USERS = str(Path.home() / ".local/share/Steam/userdata/*/config/localconfig.vdf")
# Steam's keyboard layouts (its ESteamDeckKeyboardLayout numbers) → language. QWERTY, QWERTY
# international, Dvorak and Colemak (0, 26, 27, 28) say nothing about the language.
STEAM_LAYOUTS = {1: "bg", 2: "zh_CN", 3: "zh_TW", 4: "cs", 5: "da", 6: "fi", 7: "fr", 8: "de", 9: "el",
                 10: "hu", 11: "it", 12: "ja", 13: "ko", 14: "nb", 15: "pl", 16: "pt", 17: "ro", 18: "ru",
                 19: "es", 20: "sv", 22: "tr", 23: "tr", 24: "uk", 25: "vi", 29: "bg", 30: "bg",
                 31: "zh_TW", 32: "zh_TW", 33: "ja", 34: "zh_TW"}
# KDE's (XKB) layouts → language; us, gb and others not listed say nothing.
XKB_LAYOUTS = {"latam": "es_419", "es": "es", "de": "de", "at": "de", "ch": "de", "fr": "fr", "ca": "fr_CA",
               "it": "it", "pt": "pt", "br": "pt_BR", "ru": "ru", "ua": "uk", "pl": "pl", "cz": "cs", "sk": "sk",
               "se": "sv", "no": "nb", "dk": "da", "fi": "fi", "nl": "nl", "tr": "tr", "gr": "el", "jp": "ja",
               "kr": "ko", "cn": "zh_CN", "tw": "zh_TW", "hu": "hu", "ro": "ro", "bg": "bg", "vn": "vi",
               "th": "th", "il": "he", "ara": "ar", "ir": "fa"}
_keyboard = {"at": None, "value": None, "files": {}}


def _steam_layout():
    """Steam's VR keyboard's current layout number: from config.vdf or the user's localconfig.vdf,
    whichever Steam wrote last (switching layouts saves it). Each file is read again only when
    it changed."""
    newest = None
    for f in [str(STEAM_CONFIG), *glob.glob(STEAM_USERS)]:
        try:
            mtime = os.stat(f).st_mtime
        except OSError:
            continue
        seen = _keyboard["files"].get(f)
        if not seen or seen[0] != mtime:
            m = None
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    m = re.search(r'"keyboard_layout"\s+"((?:[^"\\]|\\.)*)"', fh.read())
                layout = json.loads(m[1].replace('\\"', '"'))["currentLayout"] if m else None
            except (OSError, ValueError, KeyError, TypeError):
                layout = None
            seen = _keyboard["files"][f] = (mtime, layout)
        if seen[1] is not None and (newest is None or seen[0] > newest[0]):
            newest = seen
    return newest[1] if newest else None


def _kde_layout():
    """KDE's current layout (us, latam, …): the only one in kxkbrc, or the one KDE says is active."""
    try:
        text = (Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "kxkbrc").read_text()
    except OSError:
        return None
    m = re.search(r"^LayoutList=(.*)$", text, re.M)
    layouts = [l.strip() for l in m[1].split(",") if l.strip()] if m else []
    if len(layouts) <= 1:
        return layouts[0] if layouts else None
    try:
        r = subprocess.run(["qdbus6", "org.kde.keyboard", "/Layouts", "getLayout"],
                           capture_output=True, text=True, timeout=1)
        i = int(r.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        i = 0
    return layouts[i] if 0 <= i < len(layouts) else layouts[0]


def keyboard_language():
    """The active keyboard's language (e.g. "es"), or None when it says nothing (an English or
    unknown layout). Looked at no more than once every CHECK_EVERY seconds; between, the last
    answer. FRAME_TWEAKS_KEYBOARD=0 turns this off."""
    if os.environ.get("FRAME_TWEAKS_KEYBOARD") == "0":
        return None
    now = time.monotonic()
    if _keyboard["at"] is not None and now - _keyboard["at"] < CHECK_EVERY:
        return _keyboard["value"]
    _keyboard["at"] = now
    try:
        if "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", ""):
            layout = _kde_layout()
            _keyboard["value"] = XKB_LAYOUTS.get(layout.split("(")[0]) if layout else None
        else:
            _keyboard["value"] = STEAM_LAYOUTS.get(_steam_layout())
    except Exception:            # (a guess at the language must never stop a program)
        _keyboard["value"] = None
    return _keyboard["value"]


def wanted_languages():
    """The languages to try, best first: FRAME_TWEAKS_LANGUAGE, the active keyboard's, then
    gettext's usual variables; each also without its region (de_AT → de)."""
    if os.environ.get("FRAME_TWEAKS_LANGUAGE", "").split(".")[0] in ("en", "C", "POSIX"):
        return []                                     # (English, whatever the keyboard or session)
    names = []
    kb = keyboard_language()
    for var in ("FRAME_TWEAKS_LANGUAGE", "keyboard", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = kb or "" if var == "keyboard" else os.environ.get(var, "")
        if not value:
            continue
        for part in value.split(":"):
            code = part.split(".")[0].split("@")[0]
            if code and code not in ("C", "POSIX"):
                names += [code, code.split("_")[0]]
        if var not in ("FRAME_TWEAKS_LANGUAGE", "keyboard"):
            break                                     # (gettext: the first one set wins)
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen


def pick(languages, folder):
    """The .po file for the first of languages that has one: its own (es_MX.po), else one for
    the same language (es_419.po, es.po)."""
    for lang in languages:
        if (folder / f"{lang}.po").is_file():
            return folder / f"{lang}.po"
        base = lang.split("_")[0]
        near = sorted(folder.glob(f"{base}_*.po")) + ([folder / f"{base}.po"] if (folder / f"{base}.po").is_file() else [])
        if near:
            return near[0]
    return None


class Catalogue:
    def __init__(self, languages=None, folder=LOCALE):
        self.messages, self.header, self.language, self.file = {}, "", None, None
        f = pick(wanted_languages() if languages is None else languages, folder)
        if f:
            text = f.read_text(encoding="utf-8")
            self.messages = parse_po(text)
            m = re.search(r'msgid ""\s*msgstr ((?:".*"\s*)+)', text)
            self.header = "".join(unquote(s) for s in re.findall(r'".*"', m[1])) if m else ""
            self.language, self.file = f.stem, f

    def gettext(self, text, context=None):
        strs = self.messages.get((context, text))
        return strs[0] if strs and strs[0] else text

    def ngettext(self, singular, plural, n, context=None):
        strs = self.messages.get((context, singular))
        if strs:
            i = plural_index(n, self.header)
            if i < len(strs) and strs[i]:
                return strs[i]
        return singular if n == 1 else plural


CATALOGUE = Catalogue()


def refresh():
    """Look again at which language to use (the keyboard may have changed; no more than once
    every CHECK_EVERY seconds): True when it changed, and _() now gives the new one."""
    global CATALOGUE
    f = pick(wanted_languages(), LOCALE)
    if f == CATALOGUE.file:
        return False
    CATALOGUE = Catalogue()
    return True


def _(text):
    """text in the user's language (English if there's no translation)."""
    return CATALOGUE.gettext(text)


def N_(text):
    """Marks text for dev/i18n.py without translating it yet: for a constant made at import
    time, translated with _() where it's shown (the language can change while a program runs)."""
    return text


def ngettext(singular, plural, n):
    return CATALOGUE.ngettext(singular, plural, n)


def pgettext(context, text):
    """For text that's translated differently in different places (context tells them apart)."""
    return CATALOGUE.gettext(text, context)


def bash():
    """For lib/i18n.sh: the catalogue as a bash associative array (FT_TR), and the language
    chosen (FRAME_TWEAKS_LANG_RESOLVED; "en" for none), so scripts it starts needn't look again."""
    import shlex
    print(f"export FRAME_TWEAKS_LANG_RESOLVED={shlex.quote(CATALOGUE.language or 'en')}")
    pairs = " ".join(f"[{shlex.quote(msgid)}]={shlex.quote(strs[0])}"
                     for (ctx, msgid), strs in CATALOGUE.messages.items() if ctx is None and strs[0])
    print(f"FT_TR=({pairs})")


# ---- menu entries -------------------------------------------------------------------------------
# A Frame Tweaks menu entry (.desktop) carries every translation as Name[es_419]=… lines (the
# usual way: menus pick the system language's), and keeps its English as X-Frame-Tweaks-Name=…
# so its plain Name= can be put in the keyboard's language: at install, and again when the
# keyboard's language changes (`i18n.py menus`, run by a systemd path unit when Steam saves its
# keyboard layout; install.sh ensure_menu_entry). A menu shows what the entry said when it opened.
MENU_KEYS = ("Name", "GenericName", "Comment")
APPS = Path.home() / ".local/share/applications"
LAUNCHER_ORIGINALS = Path.home() / ".local/share/frame-tweaks/launcher-originals"   # (wallet-launcher's)


def _catalogues(folder):
    langs = []
    for f in sorted(folder.glob("*.po")):
        msgs = parse_po(f.read_text(encoding="utf-8"))
        langs.append((f.stem, msgs))
        base = f.stem.split("_")[0]
        if base != f.stem and not (folder / f"{base}.po").exists() and base not in (l for l, _m in langs):
            langs.append((base, msgs))
    return langs


def desktop(text, folder=LOCALE, catalogue=None):
    """A menu entry with its Name, GenericName and Comment in every translated language, its
    English kept (X-Frame-Tweaks-Name=…), and the plain keys in the current language."""
    cat = catalogue or CATALOGUE
    langs, out = _catalogues(folder), []
    for line in text.splitlines():
        m = re.match(rf"({'|'.join(MENU_KEYS)})=(.+)$", line)
        if not m:
            if not re.match(rf"(X-Frame-Tweaks-({'|'.join(MENU_KEYS)})|({'|'.join(MENU_KEYS)})\[[^]]+\])=", line):
                out.append(line)
            continue
        key, english = m[1], m[2]
        out += [f"{key}={cat.gettext(english)}", f"X-Frame-Tweaks-{key}={english}"]
        for lang, msgs in langs:
            tr = (msgs.get((None, english)) or [""])[0]
            if tr and tr != english and "\n" not in tr:
                out.append(f"{key}[{lang}]={tr}")
    return "\n".join(out) + "\n"


def relabel(path, catalogue=None):
    """Put a Frame Tweaks menu entry's plain Name/GenericName/Comment in the current language
    (from its X-Frame-Tweaks-… English). True if the file changed."""
    cat = catalogue or CATALOGUE
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    if "X-Frame-Tweaks-" not in text:
        return False
    out, groups = [], re.split(r"(?m)^(?=\[)", text)
    for g in groups:
        english = dict(re.findall(rf"(?m)^X-Frame-Tweaks-({'|'.join(MENU_KEYS)})=(.+)$", g))
        for key, en in english.items():
            g = re.sub(rf"(?m)^{key}=.*$", lambda _m, k=key, e=en: f"{k}={cat.gettext(e)}", g)
        out.append(g)
    new = "".join(out)
    if new == text:
        return False
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(new, encoding="utf-8")
    os.replace(tmp, path)                             # (a menu reading it sees the old or the new)
    return True


def menus(folders=(APPS, LAUNCHER_ORIGINALS)):
    """Every Frame Tweaks menu entry in the current language; the applications folder touched
    when one changed (Steam's "+" menu reads it again on its next opening)."""
    changed = [f for d in folders if d.is_dir() for f in sorted(d.glob("*.desktop")) if relabel(f)]
    if changed and APPS.is_dir():
        os.utime(APPS)
    return changed


if __name__ == "__main__":
    if sys.argv[1:] == ["bash"]:
        bash()
    elif sys.argv[1:] == ["desktop"]:
        sys.stdout.write(desktop(sys.stdin.read()))
    elif sys.argv[1:] == ["menus"]:
        for f in menus():
            print(f"{f.name}: {CATALOGUE.language or 'en'}")
    elif sys.argv[1:] == ["language"]:
        print(CATALOGUE.language or "en")
    else:
        sys.exit("i18n.py bash | language | desktop (a .desktop file in, translated out) | menus")
