#!/usr/bin/env python3
"""Translations (gettext .po files in locale/; lib/i18n.py reads them; locale/README.md).

  dev/i18n.py extract      write locale/frame-tweaks.pot: every text marked in the code
                           (Python: _("..."), ngettext, pgettext; shell: t '...') and the
                           official tweaks' manifest text
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
                           translator or a translation helper (locale/BATCH.md)
  dev/i18n.py import LANG DIR [--needs-review | --reviewed]
                           put DIR's answers (part-01.LANG.json: {"id": "text" or [forms]}) into
                           LANG.po, after checking each keeps the placeholders, tags and spacing
                           (--needs-review: mark them, e.g. machine translations: they're shown,
                           but counted as unreviewed; --reviewed: clear the mark)

A translation marked "# needs review" (a translator comment, which every gettext tool keeps) is
used like any other; only the tools count it. (Fuzzy, Poedit's "Needs work", hides it instead.)"""
import json
import ast
import re
import sys
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
SHELL = sorted({ROOT / "install.sh", *ROOT.glob("lib/*.sh"), *ROOT.glob("packs/core/*/*.sh"),
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


def from_shell():
    """{(None, msgid, None): [where, …]} from t '...' in the shell scripts."""
    out = {}
    for f in SHELL:
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


def template():
    entries = {}
    for source in (from_code(), from_shell(), from_js(), from_desktop(), from_manifests()):
        for key, where in source.items():
            entries.setdefault(key, []).extend(where)
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


PLACEHOLDER = re.compile(r"%(?:\([^)]+\))?[-+ #0]*\d*(?:\.\d+)?[sdifr%]|\{[A-Za-z_0-9]*\}|</?[a-zA-Z][^>]*>|\\n|\n")


def problems(msgid, msgstr):
    """What a translation loses of its English: placeholders, HTML tags, newlines, and the
    spaces at either end."""
    out = []
    want, got = sorted(PLACEHOLDER.findall(msgid)), sorted(PLACEHOLDER.findall(msgstr))
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
    rows = []
    for ctx, msgid, plural, block in entries_of(template()):
        if msgid == "" or (review and (ctx, msgid) not in marked) or (not every and not review and (ctx, msgid) in done):
            continue
        where = [w for l in block.splitlines() if l.startswith("#:") for w in l[2:].split()]
        row = {"id": len(rows) + 1, "ctx": ctx, "msgid": msgid, "plural": plural, "where": where}
        if (ctx, msgid) in done:                      # (--all: a second pass revises what's there)
            row["current"] = done[(ctx, msgid)] if plural else done[(ctx, msgid)][0]
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
            pairs = list(zip([row["msgid"], row["plural"]], a)) if isinstance(a, list) else [(row["msgid"], a)]
            probs = [p for en, tr in pairs for p in problems(en, tr)]
            if probs:
                bad.append(f"{part.name} #{row['id']} {row['msgid'][:50]!r}: " + "; ".join(probs))
                continue
            answers[(row["ctx"], row["msgid"])] = a
    fill(po, answers, mark)
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
    text = template()
    if cmd == "extract":
        LOCALE.mkdir(exist_ok=True)
        POT.write_text(text + "\n")
        print(f"{POT.relative_to(ROOT)}: {len(entries_of(text)) - 1} texts")
    elif cmd == "check":
        if shell_problems():
            sys.exit("\n".join(shell_problems()))
        if not POT.exists() or POT.read_text() != text + "\n":
            sys.exit("locale/frame-tweaks.pot is out of date: run dev/i18n.py extract (and update)")
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
    elif cmd == "export" and len(sys.argv) > 3:
        size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 150
        export(sys.argv[2], Path(sys.argv[3]), size, "--all" in sys.argv, "--review" in sys.argv)
    elif cmd == "import" and len(sys.argv) in (4, 5) and sys.argv[4:] in ([], ["--needs-review"], ["--reviewed"]):
        import_(sys.argv[2], Path(sys.argv[3]), {"--needs-review": "add", "--reviewed": "clear"}.get(sys.argv[4] if sys.argv[4:] else ""))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
