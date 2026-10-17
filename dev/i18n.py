#!/usr/bin/env python3
"""Translations (gettext .po files in locale/; lib/i18n.py reads them; locale/README.md).

  dev/i18n.py extract      write locale/frame-tweaks.pot: every text marked in the code
                           (Python: _("..."), ngettext, pgettext; shell: t '...') and the
                           official tweaks' manifest text; and note each text that's new or
                           whose English changed in locale/CHANGES.md (where, and what it was)
  dev/i18n.py todo [--strict]
                           before a release: what each language still has to translate (new
                           texts, changed ones) and review (--strict: fail if anything's left;
                           the release workflow)
  dev/i18n.py check        fail if the .pot is out of date (CI)
  dev/i18n.py new LANG     start locale/LANG.po from the .pot (LANG: de, pt_BR, es_419, …)
  dev/i18n.py update       bring every locale/*.po up to date with the .pot (translations kept;
                           new text untranslated; removed text kept as #~ comments)
  dev/i18n.py stats [--strict]
                           how much of each language is translated, and how much needs review
                           (--strict: fail unless every language has every text; the release)
  dev/i18n.py report       the same as Markdown, with the texts still to translate (CI's
                           "Translations needed" issue)
  dev/i18n.py export LANG DIR [--size N] [--all | --review]
                           the texts LANG.po hasn't translated yet (--all: every text, with its
                           current translation, for a review pass; --review: those marked as
                           needing review), as
                           JSON files of N entries (default 150) in DIR: part-01.json, … for a
                           translator or a translation helper (locale/BATCH.md). A text whose
                           English changed carries what it was ("was") and LANG's translation of
                           that ("was_translation"), from locale/CHANGES.md
  dev/i18n.py import LANG DIR [--needs-review | --reviewed]
                           put DIR's answers (part-01.LANG.json: {"id": "text" or [forms]}) into
                           LANG.po, after checking each keeps the placeholders, tags and spacing
                           (--needs-review: mark them, e.g. machine translations: they're shown,
                           but counted as unreviewed; --reviewed: clear the mark)

A translation marked "# needs review" (a translator comment, which every gettext tool keeps) is
used like any other; only the tools count it. (Fuzzy, Poedit's "Needs work", hides it instead.)"""
import ast
import difflib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import i18n  # noqa: E402
import sft  # noqa: E402

LOCALE = ROOT / "locale"
POT = LOCALE / "frame-tweaks.pot"
REVIEW = "# needs review"


def programs(shebang):
    """The official packs' files whose first line matches shebang (programs without .py)."""
    out = []
    for f in sorted(ROOT.glob("packs/*/*/*")):
        if f.is_file() and f.parts[-3] in ("core", "integrations", "third-party") and "__pycache__" not in f.parts:
            try:
                with open(f, "rb") as fh:
                    first = fh.readline()
            except OSError:
                continue
            if re.match(shebang, first):
                out.append(f)
    return out


CODE = sorted({*ROOT.glob("gui/*.py"), ROOT / "gui/frame-tweaks-gui.py", *ROOT.glob("lib/*.py"),
               *ROOT.glob("packs/core/*/*.py"), *ROOT.glob("packs/integrations/*/*.py"), *ROOT.glob("packs/third-party/*/*.py"),
               *programs(rb"#!.*python")})
GET_SH = ROOT / "get.sh"           # (the bootstrap: its texts carry their own translations, below)
SHELL = sorted({ROOT / "install.sh", GET_SH, *ROOT.glob("lib/*.sh"), *ROOT.glob("packs/core/*/*.sh"),
                *ROOT.glob("packs/integrations/*/*.sh"), *ROOT.glob("packs/third-party/*/*.sh"), *programs(rb"#!.*(/bash|/sh\b|env bash)")})
JS = sorted(p for pack in ("core", "integrations", "third-party") for p in ROOT.glob(f"packs/{pack}/*/*.js"))
DESKTOP = sorted([*ROOT.glob("share/applications/*.desktop"),
                  *(p for pack in ("core", "integrations", "third-party") for p in ROOT.glob(f"packs/{pack}/*/*.desktop"))])
# SteamVR dashboard patches: T('text') where it's shown, N('text') in a constant (the same rule as
# vr-dashboard/sft-dashboard's, which sends the translations into the dashboard).
JS_TEXT = re.compile(r"""\b[TN]\(\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")\s*\)""")
# t 'text' or t "text" (no $ in it): see lib/i18n.sh
T_CALL = re.compile(r"""(?:^|[\s;&|(`])t\s+(?:'([^']*)'|"((?:[^"\\$`]|\\.)*)"(?=[\s;&|)`]|$))""", re.M)
T_DOLLAR = re.compile(r"""(?:^|[\s;&|(`])t\s+"(?:[^"\\]|\\.)*\$""", re.M)
FUNCS = {"_": ("msgid",), "N_": ("msgid",), "NP_": ("msgctxt", "msgid"), "ngettext": ("msgid", "msgid_plural"), "pgettext": ("msgctxt", "msgid")}


def quote(s):
    """Text as a .po string literal (long or multi-line text split over lines, as gettext does)."""
    esc = s.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")
    parts = esc.split("\n")
    lines = [p + ("\\n" if i < len(parts) - 1 else "") for i, p in enumerate(parts)]
    lines = [l for l in lines if l]
    if len(lines) <= 1 and len(esc) < 70:
        return f'"{esc}"'.replace("\n", "\\n")
    return '""\n' + "\n".join(f'"{l}"' for l in lines)


def from_code():
    """{(context, msgid, plural): [where, …]} from the marked calls in the code."""
    out = {}
    for f in dict.fromkeys(CODE):
        try:
            tree = ast.parse(f.read_text(), str(f))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS):
                continue
            args = node.args[:len(FUNCS[node.func.id])]
            if len(args) < len(FUNCS[node.func.id]) or not all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in args):
                continue
            vals = dict(zip(FUNCS[node.func.id], (a.value for a in args)))
            key = (vals.get("msgctxt"), vals["msgid"], vals.get("msgid_plural"))
            out.setdefault(key, []).append(f"{f.relative_to(ROOT)}:{node.lineno}")
    return out


def from_shell(files=None):
    """{(None, msgid, None): [where, …]} from t '...' in the shell scripts."""
    out = {}
    for f in SHELL if files is None else files:
        text = f.read_text(errors="replace")
        for m in T_CALL.finditer(text):
            if re.search(r"(^|\s)#", text[text.rfind("\n", 0, m.start()) + 1:m.start()]):
                continue                                   # (in a comment)
            msgid = m[1] if m[1] is not None else re.sub(r'\\([\\"$`])', r"\1", m[2])
            if msgid:
                line = text.count("\n", 0, m.start()) + 1
                out.setdefault((None, msgid, None), []).append(f"{f.relative_to(ROOT)}:{line}")
    return out


def js_string(body):
    try:
        return json.loads('"' + body.replace("\\'", "'").replace('"', '\\"').replace('\\\\"', '\\"') + '"')
    except ValueError:
        return body


def from_js():
    """{(None, msgid, None): [where, …]} from T('...') / N('...') in the dashboard patches."""
    out = {}
    for f in JS:
        text = f.read_text()
        for m in JS_TEXT.finditer(text):
            msgid = js_string(m[1] if m[1] is not None else m[2])
            if msgid:
                out.setdefault((None, msgid, None), []).append(f"{f.relative_to(ROOT)}:{text.count(chr(10), 0, m.start()) + 1}")
    return out


DESKTOP_KEYS = ("Name", "GenericName", "Comment")


def from_desktop():
    """{(None, msgid, None): [where, …]} from the menu entries' Name, GenericName and Comment."""
    out = {}
    for f in DESKTOP:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            m = re.match(rf"({'|'.join(DESKTOP_KEYS)})=(.+)$", line)
            if m:
                out.setdefault((None, m[2], None), []).append(f"{f.relative_to(ROOT)}:{n}")
    return out


def shell_problems():
    """t "...$..." (a value inside the text): it can't be translated."""
    out = []
    for f in SHELL:
        text = f.read_text(errors="replace")
        for m in T_DOLLAR.finditer(text):
            if re.search(r"(^|\s)#", text[text.rfind("\n", 0, m.start()) + 1:m.start()]):
                continue
            out.append(f"{f.relative_to(ROOT)}:{text.count(chr(10), 0, m.start()) + 1}: "
                       "a $value inside t \"...\": use %s and pass it after the text")
    return out


def from_manifests():
    """The official tweaks' text the window shows: titles, summaries, what, why, categories,
    settings (translated through sft.tr, the same msgids)."""
    out = {}

    def add(text, where):
        if isinstance(text, str) and re.search(r"[^\W\d_]", text):     # (not "1.5": nothing to translate)
            out.setdefault((None, text, None), []).append(where)

    for pack in sft.OFFICIAL_PACKS:
        info, folders, _ = sft.read_pack(pack)
        for text in (info["name"], info["about"], *info["categories"]):
            add(text, f"{pack.relative_to(ROOT)}/pack.md")
        for d in folders:
            c, _ = sft.read_tweak(d)
            if not c:
                continue
            where = f"{d.relative_to(ROOT)}/README.md"
            for k in ("title", "desc", "what", "why", "run_label", "category", "sudo"):
                if not (k == "sudo" and c.get(k) == "homebrew"):        # (a keyword: lib/sft.py sudo_note)
                    add(c.get(k), where)
            if "|" in c.get("source", ""):
                add(c["source"].split("|", 1)[0], where)              # (uses, from, styled after, …)
            st = c.get("settings") or {}
            add(st.get("about"), where)
            add(st.get("note"), where)
            for o in st.get("options", []):
                add(o.get("title"), where)
                for ch in o.get("choices", []):
                    add(ch.get("label"), where)
            for a in st.get("actions", []):
                add(a.get("label"), where)
                add(a.get("about"), where)
    return out


def collect():
    """{(context, msgid, plural): [file:line, …]}: every marked text, and where it is."""
    entries = {}
    for source in (from_code(), from_shell(), from_js(), from_desktop(), from_manifests()):
        for key, where in source.items():
            entries.setdefault(key, []).extend(where)
    return entries


def template(entries=None):
    entries = collect() if entries is None else entries
    lines = ['# Frame Tweaks: text to translate. Made by dev/i18n.py extract; don\'t edit by hand.',
             '# Translators: copy to LANG.po (dev/i18n.py new LANG), see locale/README.md.',
             'msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', '']
    # Where each text is: its files, not their lines. With line numbers every edit above a text
    # moved its reference, and the template (and every .po) changed without a text changing; now
    # they change only when a text does. (Sorted by file, then text, so code moving in a file
    # leaves the order alone too.)
    files = {key: list(dict.fromkeys(re.sub(r":\d+$", "", w) for w in where)) for key, where in entries.items()}
    for (ctx, msgid, plural), where in sorted(files.items(), key=lambda e: (e[1][0], e[0][1], e[0][0] or "")):
        lines.append("#: " + " ".join(where))
        if ctx:
            lines.append("msgctxt " + quote(ctx))
        lines.append("msgid " + quote(msgid))
        if plural:
            lines += ["msgid_plural " + quote(plural), 'msgstr[0] ""', 'msgstr[1] ""', ""]
        else:
            lines += ['msgstr ""', ""]
    return "\n".join(lines)


def entries_of(text):
    """[(context, msgid, plural, block)] of a .po/.pot text (block: the entry's own lines)."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        ctx = re.search(r'^msgctxt ((?:".*"\n?)+)', block, re.M)
        mid = re.search(r'^msgid ((?:".*"\n?)+)', block, re.M)
        plu = re.search(r'^msgid_plural ((?:".*"\n?)+)', block, re.M)
        if not mid:
            continue
        j = lambda m: "".join(i18n.unquote(s) for s in re.findall(r'".*"', m[1])) if m else None
        out.append((j(ctx), j(mid), j(plu), block))
    return out


# ---- English changes waiting for translation (locale/CHANGES.md) -------------------------------
# Translations are done just before a release, all at once (CONTRIBUTING.md, Translations): in
# between, the English changes freely. So each extract notes what it changed, where, and what a
# changed text was; translators then adjust the old translation instead of hunting for the change.
CHANGES_HEAD = """# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\\n` is a new line). Don't edit by hand."""
SIMILAR = 0.5          # how alike a gone text and a new one in the same file are, to be one text changed
ENTRY = re.compile(r"^- (New|Changed) in `([^`]*)`$")
FIELD = re.compile(r"^  - (context|was|now|plural): (.*)$")


def changes_file():
    return LOCALE / "CHANGES.md"


def read_changes():
    """[{date, where, ctx, was, now, plural}] of locale/CHANGES.md (was: None for a new text)."""
    f = changes_file()
    if not f.exists():
        return []
    out, date, cur = [], None, None
    for line in f.read_text().splitlines():
        if line.startswith("## "):
            date = line[3:].strip()
        elif m := ENTRY.match(line):
            cur = {"date": date, "where": m[2], "ctx": None, "was": None, "now": None, "plural": None}
            out.append(cur)
        elif (m := FIELD.match(line)) and cur is not None:
            cur["ctx" if m[1] == "context" else m[1]] = json.loads(m[2])
    return [e for e in out if e["now"] is not None]


def write_changes(log):
    lines = [CHANGES_HEAD]
    if not log:
        lines += ["", "Nothing waiting: no English text has changed since the languages last caught up."]
    for date in sorted({e["date"] for e in log}):
        lines += ["", f"## {date}"]
        for e in sorted((e for e in log if e["date"] == date), key=lambda e: (e["where"], e["now"])):
            lines.append(f"- {'New' if e['was'] is None else 'Changed'} in `{e['where']}`")
            for field, name in (("ctx", "context"), ("was", "was"), ("now", "now"), ("plural", "plural")):
                if e[field] is not None:
                    lines.append(f"  - {name}: {json.dumps(e[field], ensure_ascii=False)}")
    changes_file().write_text("\n".join(lines) + "\n")


def translated_everywhere(log):
    """The log without the texts every language has translated (none without a language)."""
    done = [i18n.parse_po(po.read_text()) for po in sorted(LOCALE.glob("*.po"))]
    return [e for e in log if not (done and all((e["ctx"], e["now"]) in d for d in done))]


def tidy_changes():
    """After translations came in: drop what's done from the log (if there is one)."""
    if changes_file().exists():
        write_changes(translated_everywhere(read_changes()))


def log_changes(old_pot, entries, today=None):
    """Note in the log what this extract changed, against the template it replaces (old_pot):
    each text it didn't have, as a change of the gone text it's most like in the same file (or
    new), where it is now; a text changed again before it was translated keeps what it first was;
    one changed back, or gone, goes."""
    old = {(c, m): (p, {f for l in b.splitlines() if l.startswith("#:") for f in l[2:].split()})
           for c, m, p, b in entries_of(old_pot) if m}
    new = {(c, m): (p, where) for (c, m, p), where in entries.items()}
    added = [k for k in new if k not in old]
    gone = [k for k in old if k not in new]
    scored = []
    for a in added:
        files = {re.sub(r":\d+$", "", w) for w in new[a][1]}
        for g in gone:
            if g[0] == a[0] and files & old[g][1]:
                score = difflib.SequenceMatcher(None, g[1], a[1]).ratio()
                if score >= SIMILAR:
                    scored.append((score, a, g))
    pairs, used = {}, set()
    for _score, a, g in sorted(scored, key=lambda s: -s[0]):
        if a not in pairs and g not in used:
            pairs[a] = g
            used.add(g)
    log = read_changes()
    today = today or time.strftime("%Y-%m-%d")

    def logged(key):
        return next((e for e in log if (e["ctx"], e["now"]) == key), None)
    for a in added:
        plural, where = new[a][0], new[a][1][0]
        if a in pairs and (e := logged(pairs[a])):              # changed again: still what it was
            e.update(now=a[1], plural=plural, where=where, date=today)
            if e["was"] == a[1]:
                log.remove(e)                                  # (back to what's translated)
        elif a in pairs:
            log.append({"date": today, "where": where, "ctx": a[0], "was": pairs[a][1], "now": a[1], "plural": plural})
        elif not logged(a):
            log.append({"date": today, "where": where, "ctx": a[0], "was": None, "now": a[1], "plural": plural})
    for g in gone:
        if g not in used and (e := logged(g)):
            log.remove(e)                                      # (waiting, and gone again)
    write_changes(translated_everywhere(log))


def earlier_translations(text):
    """{(context, msgid): [msgstr…]} of a .po text, its #~ (removed) texts included."""
    gone = "\n\n".join(re.sub(r"^#~ ", "", b, flags=re.M) for b in obsolete(text))
    return {**i18n.parse_po(gone), **i18n.parse_po(text)}


def todo(text):
    """[(language, new, changed, to review)]: what each language still has to do."""
    want = [(c, m) for c, m, _, _ in entries_of(text) if m]
    was = {(e["ctx"], e["now"]): e["was"] for e in read_changes() if e["was"] is not None}
    out = []
    for po in sorted(LOCALE.glob("*.po")):
        t = po.read_text()
        done, before = i18n.parse_po(t), earlier_translations(t)
        missing = [k for k in want if k not in done]
        changed = sum(1 for k in missing if k in was and (k[0], was[k]) in before)
        out.append((po.stem, len(missing) - changed, changed, len(needs_review(t))))
    return out


# ---- get.sh: its texts come before Frame Tweaks' translations are on the machine -----------------
GET_SH_BLOCK = re.compile(r"(\n *# BEGIN translations[^\n]*\n)(.*?)(\n *# END translations)", re.S)


def bash_word(s):
    return "$'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\t", "\\t") + "'"


def get_sh_block():
    """get.sh's translations block: its texts, in each language that has them."""
    wanted = sorted({m for (_c, m, _p) in from_shell([GET_SH])})
    pairs, langs = [], []
    for po in sorted(LOCALE.glob("*.po")):
        done = i18n.parse_po(po.read_text())
        mine = [(m, done[(None, m)][0]) for m in wanted if done.get((None, m), [""])[0]]
        if mine:
            langs.append(po.stem)
            pairs += [(f"{po.stem}|{m}", tr) for m, tr in mine]
    lines = [f'    GET_LANGS="{" ".join(langs)}"', "    declare -gA GET_TR=("]
    lines += [f"        [{bash_word(k)}]={bash_word(v)}" for k, v in pairs]
    return "\n".join(lines + ["    )"])


def get_sh_text(text):
    """get.sh's text with its block as the translations have it now."""
    return GET_SH_BLOCK.sub(lambda m: m[1] + get_sh_block() + m[3], text, count=1)


def write_get_sh():
    """Bring get.sh's block up to date (only from the repo's own translations: tests use others)."""
    if LOCALE.resolve() == (ROOT / "locale").resolve() and GET_SH.exists():
        text = GET_SH.read_text()
        new = get_sh_text(text)
        if new != text:
            GET_SH.write_text(new)


def obsolete(text):
    """The #~ blocks of a .po text: removed texts, kept for their translations."""
    return [b for b in re.split(r"\n\s*\n", text.strip()) if b.lstrip().startswith("#~")]


def update(po, pot_text):
    """po's translations, laid out on the template's entries. Texts removed before stay as #~
    comments, and are in use again if the template has them again."""
    text = po.read_text()
    kept = entries_of("\n\n".join(re.sub(r"^#~ ", "", b, flags=re.M) for b in obsolete(text)))
    old = {(c, m): b for c, m, _, b in kept + entries_of(text) if not b.lstrip().startswith("#~")}
    header = next((b for c, m, _, b in entries_of(text) if m == ""), None)
    out, used = [], set()
    for ctx, msgid, plural, block in entries_of(pot_text):
        if msgid == "":
            out.append(header or block)
            continue
        prev = old.get((ctx, msgid))
        if prev:
            refs = [l for l in block.splitlines() if l.startswith("#:")]
            mine = [l for l in prev.splitlines() if not l.startswith("#:")]
            notes = [l for l in mine if l == "#" or l.startswith("# ")]      # (translator comments first)
            out.append("\n".join(notes + refs + [l for l in mine if l not in notes]))
            used.add((ctx, msgid))
        else:
            out.append(block)
    # (translated: a msgstr with text, on its line or, when long, on the next: msgstr "" "…")
    gone = [b for k, b in old.items() if k not in used and k[1] != "" and re.search(r'^msgstr(\[\d+\])? (""\n)?"(?!")', b, re.M)]
    out += ["\n".join("#~ " + l for l in b.splitlines() if not l.startswith("#:")) for b in gone]
    po.write_text("\n\n".join(out) + "\n")
    tidy_changes()
    write_get_sh()


PLACEHOLDER = re.compile(r"\{[A-Za-z_0-9]*\}|</?[a-zA-Z][^>]*>|\\n|\n")
# A text printf or Python's % formats has a conversion (%s, %d, %(name)s) or a %% in its English;
# in other text (a tweak's manifest, say) a % is just a percent sign: "starts again 1% below".
FORMAT_TEXT = re.compile(r"%(?:\([^)]+\))?[-+#0]*\d*(?:\.\d+)?[sdifxXr]|%%")
# Its conversions as printf reads them, space flag included: "100 % de" in a format text is one.
CONVERSION = re.compile(r"%(?:\([^)]+\))?[-+ #0']*\d*(?:\.\d+)?[sdifxXr%]")


def placeholders(english, text):
    found = PLACEHOLDER.findall(text)
    if FORMAT_TEXT.search(english):
        found += CONVERSION.findall(text)
    return sorted(found)


def problems(msgid, msgstr):
    """What a translation loses of its English: placeholders, HTML tags, newlines, and the
    spaces at either end."""
    out = []
    want, got = placeholders(msgid, msgid), placeholders(msgid, msgstr)
    if want != got:
        out.append(f"placeholders/tags {want} became {got}")
    for side, f in (("start", lambda x: x[:len(x) - len(x.lstrip())]), ("end", lambda x: x[len(x.rstrip()):])):
        if f(msgid) != f(msgstr):
            out.append(f"spacing at the {side} differs")
    return out


def needs_review(text):
    """{(context, msgid)} of a .po text's translated entries marked "# needs review"."""
    done = i18n.parse_po(text)
    return {(c, m) for c, m, _, b in entries_of(text)
            if REVIEW in b.splitlines() and (c, m) in done and not b.lstrip().startswith("#~")}


def export(lang, outdir, size=150, every=False, review=False):
    po = LOCALE / f"{lang}.po"
    if review and not po.exists():
        sys.exit(f"no locale/{po.name}: nothing of {lang}'s to review")
    done = i18n.parse_po(po.read_text()) if po.exists() else {}
    marked = needs_review(po.read_text()) if review else set()
    before = earlier_translations(po.read_text()) if po.exists() else {}
    was = {(e["ctx"], e["now"]): e["was"] for e in read_changes() if e["was"] is not None}
    rows = []
    for ctx, msgid, plural, block in entries_of(template()):
        if msgid == "" or (review and (ctx, msgid) not in marked) or (not every and not review and (ctx, msgid) in done):
            continue
        where = [w for l in block.splitlines() if l.startswith("#:") for w in l[2:].split()]
        row = {"id": len(rows) + 1, "ctx": ctx, "msgid": msgid, "plural": plural, "where": where}
        if (ctx, msgid) in done:                      # (--all: a second pass revises what's there)
            row["current"] = done[(ctx, msgid)] if plural else done[(ctx, msgid)][0]
        elif (ctx, msgid) in was:                     # (its English changed: what it was, to adjust)
            row["was"] = was[(ctx, msgid)]
            if (ctx, row["was"]) in before:
                row["was_translation"] = before[(ctx, row["was"])] if plural else before[(ctx, row["was"])][0]
        rows.append(row)
    outdir.mkdir(parents=True, exist_ok=True)
    parts = [rows[i:i + size] for i in range(0, len(rows), size)]
    for n, part in enumerate(parts, 1):
        (outdir / f"part-{n:02d}.json").write_text(json.dumps(part, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(rows)} texts in {len(parts)} files in {outdir}")


def fill(po, answers, mark=None):
    """Write answers ({(ctx, msgid): str or [forms]}) into the .po file's entries; mark "add"
    puts "# needs review" on them, "clear" takes it off."""
    out, text = [], po.read_text()
    for ctx, msgid, plural, block in entries_of(text):
        a = answers.get((ctx, msgid)) if msgid else None
        if a is not None and not block.lstrip().startswith("#~"):
            keep, seen_msgstr = [], False
            for l in block.splitlines():
                if l.startswith("msgstr"):
                    seen_msgstr = True
                    continue
                if seen_msgstr and l.startswith('"'):
                    continue
                keep.append(l)
            keep = [l for l in keep if l != "#, fuzzy" and (mark is None or l != REVIEW)]
            if mark == "add":
                keep.insert(0, REVIEW)
            if plural:
                forms = a if isinstance(a, list) else [a, a]
                keep += [f"msgstr[{i}] " + quote(f) for i, f in enumerate(forms)]
            else:
                keep.append("msgstr " + quote(a if isinstance(a, str) else a[0]))
            block = "\n".join(keep)
        out.append(block)
    po.write_text("\n\n".join(out + obsolete(text)) + "\n")


def import_(lang, outdir, mark=None):
    po = LOCALE / f"{lang}.po"
    if not po.exists():
        sys.exit(f"no locale/{po.name}: dev/i18n.py new {lang} first")
    update(po, template() + "\n")
    answers, bad = {}, []
    for part in sorted(outdir.glob("part-[0-9][0-9].json")):
        mine = outdir / f"{part.stem}.{lang}.json"
        if not mine.exists():
            print(f"{mine.name}: missing, skipped")
            continue
        rows, got = json.loads(part.read_text()), json.loads(mine.read_text())
        for row in rows:
            a = got.get(str(row["id"]))
            if a in (None, "", []):
                continue
            if isinstance(a, list) and (row["plural"] is None or not all(isinstance(x, str) for x in a)):
                bad.append(f"{part.name} #{row['id']} {row['msgid'][:50]!r}: plural forms given for a text without a plural")
                continue
            pairs = list(zip([row["msgid"], row["plural"]], a)) if isinstance(a, list) else [(row["msgid"], a)]
            probs = [p for en, tr in pairs for p in problems(en, tr)]
            if probs:
                bad.append(f"{part.name} #{row['id']} {row['msgid'][:50]!r}: " + "; ".join(probs))
                continue
            answers[(row["ctx"], row["msgid"])] = a
    fill(po, answers, mark)
    tidy_changes()
    write_get_sh()
    print(f"locale/{po.name}: {len(answers)} texts put in"
          + {"add": ", marked as needing review", "clear": ", marked as reviewed"}.get(mark, ""))
    if bad:
        print(f"{len(bad)} left out (fix them in the answer files, then import again):")
        print("\n".join("  " + b for b in bad))


def progress(text):
    """[(language, texts, translated, needing review, [msgids not translated])] per locale/*.po."""
    want = [(c, m) for c, m, _, _ in entries_of(text) if m]
    out = []
    for po in sorted(LOCALE.glob("*.po")):
        t = po.read_text()
        done = i18n.parse_po(t)
        out.append((po.stem, len(want), sum(k in done for k in want), len(needs_review(t)),
                    [m for k in want if k not in done for m in [k[1]]]))
    return out


def report(text, most=40):
    """Markdown: each language's progress, and the texts it still lacks (the first `most`)."""
    lines = ["Texts that need translating, or a translation that needs a person's review, after "
             "the latest change on main. Translators: locale/README.md and locale/BATCH.md.", ""]
    for lang, total, done, review, missing in progress(text):
        lines.append(f"### {lang}: {done} of {total} translated" + (f", {review} need review" if review else ""))
        if missing:
            lines += ["", "Not translated yet:", ""] + [f"- `{m[:120]}`" for m in missing[:most]]
            if len(missing) > most:
                lines.append(f"- … and {len(missing) - most} more (`dev/i18n.py export {lang} DIR`)")
        if review:
            lines += ["", f"To review: `dev/i18n.py export {lang} DIR --review`, then import with `--reviewed`."]
        lines.append("")
    return "\n".join(lines)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    entries = collect()
    text = template(entries)
    if cmd == "extract":
        LOCALE.mkdir(exist_ok=True)
        old = POT.read_text() if POT.exists() else None
        POT.write_text(text + "\n")
        print(f"{POT.relative_to(ROOT)}: {len(entries_of(text)) - 1} texts")
        if old is not None and old != text + "\n":
            log_changes(old, entries)
            n = len(read_changes())
            print(f"{changes_file().relative_to(ROOT)}: {n} English change{'s' * (n != 1)} waiting for translation")
    elif cmd == "check":
        if shell_problems():
            sys.exit("\n".join(shell_problems()))
        if not POT.exists() or POT.read_text() != text + "\n":
            sys.exit("locale/frame-tweaks.pot is out of date: run dev/i18n.py extract (and update)")
        if GET_SH.exists() and get_sh_text(GET_SH.read_text()) != GET_SH.read_text():
            sys.exit("get.sh's own translations are out of date: run dev/i18n.py update")
        print("translation template up to date")
    elif cmd == "new" and len(sys.argv) > 2 and re.fullmatch(r"[a-z]{2,3}(_([A-Z]{2}|[0-9]{3}))?", sys.argv[2]):
        po = LOCALE / f"{sys.argv[2]}.po"
        if po.exists():
            sys.exit(f"{po.relative_to(ROOT)} exists: dev/i18n.py update brings it up to date")
        text = re.sub(r"\A(#.*\n)+", f"# Frame Tweaks: the {sys.argv[2]} translation (locale/README.md).\n", text)
        po.write_text(text.replace('"Content-Type: text/plain; charset=UTF-8\\n"',
                                   f'"Language: {sys.argv[2]}\\n"\n"Content-Type: text/plain; charset=UTF-8\\n"\n'
                                   '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"') + "\n")
        print(f"{po.relative_to(ROOT)}: started; check its Plural-Forms line for your language")
    elif cmd == "update":
        for po in sorted(LOCALE.glob("*.po")):
            update(po, text)
            print(f"{po.relative_to(ROOT)}: updated")
    elif cmd == "stats":
        short = False
        for lang, total, done, review, _missing in progress(text):
            print(f"{lang}: {done} of {total} translated ({100 * done // max(total, 1)} %)"
                  + (f", {review} need review" if review else ""))
            short = short or done < total
        if not list(LOCALE.glob("*.po")):
            print("no translations yet")
        if short and "--strict" in sys.argv:
            sys.exit("not every text is translated: dev/i18n.py export LANG DIR (locale/BATCH.md)")
    elif cmd == "report":
        print(report(text))
    elif cmd == "todo":
        rows, log = todo(text), read_changes()
        print("Translation work before the next release (locale/BATCH.md):")
        for lang, new, changed, review in rows:
            left = new + changed
            print(f"  {lang:8} " + (f"{left} to translate ({new} new, {changed} changed)" if left else "complete")
                  + (f"; {review} to review (not needed for a release)" if review else ""))
        if not rows:
            print("  no translations yet")
        print(f"English changes waiting ({changes_file().relative_to(ROOT)}): "
              f"{sum(e['was'] is None for e in log)} new, {sum(e['was'] is not None for e in log)} changed")
        if any(new + changed for _l, new, changed, _r in rows):
            print("Next: dev/i18n.py export LANG DIR, translate, dev/i18n.py import LANG DIR")
            if "--strict" in sys.argv:
                sys.exit("not every text is translated (dev/i18n.py todo)")
    elif cmd == "export" and len(sys.argv) > 3:
        size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 150
        export(sys.argv[2], Path(sys.argv[3]), size, "--all" in sys.argv, "--review" in sys.argv)
    elif cmd == "import" and len(sys.argv) in (4, 5) and sys.argv[4:] in ([], ["--needs-review"], ["--reviewed"]):
        import_(sys.argv[2], Path(sys.argv[3]), {"--needs-review": "add", "--reviewed": "clear"}.get(sys.argv[4] if sys.argv[4:] else ""))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
