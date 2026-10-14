"""Translations: GNU gettext's message catalogues (.po files in locale/), read directly.

Translators edit locale/<language>.po (e.g. de.po, pt_BR.po) made from the template
locale/frame-tweaks.pot (dev/i18n.py makes and updates both; see locale/README.md). Code marks
text with _("..."), ngettext(singular, plural, n) or pgettext(context, "..."); text without a
translation stays English. The language is the usual one: LANGUAGE, LC_ALL, LC_MESSAGES or LANG
(FRAME_TWEAKS_LANGUAGE first, to try a translation without changing the session's).

No compile step and no dependency: the .po files are read as they are (fuzzy entries skipped)."""
import ast
import gettext
import os
import re
from pathlib import Path

LOCALE = Path(__file__).resolve().parent.parent / "locale"


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


def wanted_languages():
    """The languages to try, best first: FRAME_TWEAKS_LANGUAGE, then gettext's usual variables;
    each also without its region (de_AT → de)."""
    names = []
    for var in ("FRAME_TWEAKS_LANGUAGE", "LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if not value:
            continue
        for part in value.split(":"):
            code = part.split(".")[0].split("@")[0]
            if code and code not in ("C", "POSIX"):
                names += [code, code.split("_")[0]]
        if var != "FRAME_TWEAKS_LANGUAGE":
            break                                     # (gettext: the first one set wins)
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen


class Catalogue:
    def __init__(self, languages=None, folder=LOCALE):
        self.messages, self.header, self.language = {}, "", None
        for lang in wanted_languages() if languages is None else languages:
            f = folder / f"{lang}.po"
            if f.is_file():
                text = f.read_text(encoding="utf-8")
                self.messages = parse_po(text)
                m = re.search(r'msgid ""\s*msgstr ((?:".*"\s*)+)', text)
                self.header = "".join(unquote(s) for s in re.findall(r'".*"', m[1])) if m else ""
                self.language = lang
                break

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


def _(text):
    """text in the user's language (English if there's no translation)."""
    return CATALOGUE.gettext(text)


def ngettext(singular, plural, n):
    return CATALOGUE.ngettext(singular, plural, n)


def pgettext(context, text):
    """For text that's translated differently in different places (context tells them apart)."""
    return CATALOGUE.gettext(text, context)
