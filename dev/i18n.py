#!/usr/bin/env python3
"""Translations (gettext .po files in locale/; lib/i18n.py reads them; locale/README.md).

  dev/i18n.py extract      write locale/frame-tweaks.pot: every text marked in the code
                           (Python: _("..."), ngettext, pgettext; shell: t '...') and the
                           official tweaks' manifest text
  dev/i18n.py check        fail if the .pot is out of date (CI)
  dev/i18n.py new LANG     start locale/LANG.po from the .pot (LANG: de, pt_BR, …)
  dev/i18n.py update       bring every locale/*.po up to date with the .pot (translations kept;
                           new text untranslated; removed text kept as #~ comments)
  dev/i18n.py stats        how much of each language is translated
  dev/i18n.py export LANG DIR [--size N] [--all]
                           the texts LANG.po hasn't translated yet (--all: every text), as
                           JSON files of N entries (default 150) in DIR: part-01.json, … for a
                           translator or a translation helper (docs/claude/i18n-translating.md)
  dev/i18n.py import LANG DIR
                           put DIR's answers (part-01.LANG.json: {"id": "text" or [forms]}) into
                           LANG.po, after checking each keeps the placeholders, tags and spacing"""
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


def programs(shebang):
    """The official packs' files whose first line matches shebang (programs without .py)."""
    out = []
    for f in sorted(ROOT.glob("packs/*/*/*")):
        if f.is_file() and f.parts[-3] in ("original", "integrations", "third-party") and "__pycache__" not in f.parts:
            try:
                with open(f, "rb") as fh:
                    first = fh.readline()
            except OSError:
                continue
            if re.match(shebang, first):
                out.append(f)
    return out


CODE = sorted({*ROOT.glob("gui/*.py"), ROOT / "gui/frame-tweaks-gui.py", *ROOT.glob("lib/*.py"),
               *ROOT.glob("packs/original/*/*.py"), *ROOT.glob("packs/integrations/*/*.py"), *ROOT.glob("packs/third-party/*/*.py"),
               *programs(rb"#!.*python")})
SHELL = sorted({ROOT / "install.sh", *ROOT.glob("lib/*.sh"), *ROOT.glob("packs/original/*/*.sh"),
                *ROOT.glob("packs/integrations/*/*.sh"), *ROOT.glob("packs/third-party/*/*.sh"), *programs(rb"#!.*(/bash|/sh\b|env bash)")})
# t 'text' or t "text" (no $ in it): see lib/i18n.sh
T_CALL = re.compile(r"""(?:^|[\s;&|(`])t\s+(?:'([^']*)'|"((?:[^"\\$`]|\\.)*)"(?=[\s;&|)`]|$))""", re.M)
T_DOLLAR = re.compile(r"""(?:^|[\s;&|(`])t\s+"(?:[^"\\]|\\.)*\$""", re.M)
FUNCS = {"_": ("msgid",), "N_": ("msgid",), "ngettext": ("msgid", "msgid_plural"), "pgettext": ("msgctxt", "msgid")}


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
        for cat in info["categories"]:
            add(cat, f"{pack.relative_to(ROOT)}/pack.md")
        for d in folders:
            c, _ = sft.read_tweak(d)
            if not c:
                continue
            where = f"{d.relative_to(ROOT)}/README.md"
            for k in ("title", "desc", "what", "why", "run_label", "category"):
                add(c.get(k), where)
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
    for source in (from_code(), from_shell(), from_manifests()):
        for key, where in source.items():
            entries.setdefault(key, []).extend(where)
    lines = ['# Frame Tweaks: text to translate. Made by dev/i18n.py extract; don\'t edit by hand.',
             '# Translators: copy to LANG.po (dev/i18n.py new LANG), see locale/README.md.',
             'msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', '']
    for (ctx, msgid, plural), where in sorted(entries.items(), key=lambda e: (e[1][0], e[0][1])):
        lines.append("#: " + " ".join(dict.fromkeys(where)))
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


def update(po, pot_text):
    """po's translations, laid out on the template's entries."""
    old = {(c, m): b for c, m, _, b in entries_of(po.read_text()) if not b.lstrip().startswith("#~")}
    header = next((b for c, m, _, b in entries_of(po.read_text()) if m == ""), None)
    out, used = [], set()
    for ctx, msgid, plural, block in entries_of(pot_text):
        if msgid == "":
            out.append(header or block)
            continue
        prev = old.get((ctx, msgid))
        if prev:
            refs = [l for l in block.splitlines() if l.startswith("#:")]
            out.append("\n".join(refs + [l for l in prev.splitlines() if not l.startswith("#:")]))
            used.add((ctx, msgid))
        else:
            out.append(block)
    gone = [b for k, b in old.items() if k not in used and k[1] != "" and re.search(r'^msgstr(\[\d+\])? "(?!")', b, re.M)]
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


def export(lang, outdir, size=150, every=False):
    done = {k for k, v in i18n.parse_po((LOCALE / f"{lang}.po").read_text()).items()} if (LOCALE / f"{lang}.po").exists() else set()
    rows = []
    for ctx, msgid, plural, block in entries_of(template()):
        if msgid == "" or (not every and (ctx, msgid) in done):
            continue
        where = [w for l in block.splitlines() if l.startswith("#:") for w in l[2:].split()]
        rows.append({"id": len(rows) + 1, "ctx": ctx, "msgid": msgid, "plural": plural, "where": where})
    outdir.mkdir(parents=True, exist_ok=True)
    parts = [rows[i:i + size] for i in range(0, len(rows), size)]
    for n, part in enumerate(parts, 1):
        (outdir / f"part-{n:02d}.json").write_text(json.dumps(part, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(rows)} texts in {len(parts)} files in {outdir}")


def fill(po, answers):
    """Write answers ({(ctx, msgid): str or [forms]}) into the .po file's entries."""
    out = []
    for ctx, msgid, plural, block in entries_of(po.read_text()):
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
            keep = [l for l in keep if l != "#, fuzzy"]
            if plural:
                forms = a if isinstance(a, list) else [a, a]
                keep += [f"msgstr[{i}] " + quote(f) for i, f in enumerate(forms)]
            else:
                keep.append("msgstr " + quote(a if isinstance(a, str) else a[0]))
            block = "\n".join(keep)
        out.append(block)
    po.write_text("\n\n".join(out) + "\n")


def import_(lang, outdir):
    po = LOCALE / f"{lang}.po"
    if not po.exists():
        sys.exit(f"no {po.relative_to(ROOT)}: dev/i18n.py new {lang} first")
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
    fill(po, answers)
    print(f"{po.relative_to(ROOT)}: {len(answers)} texts put in")
    if bad:
        print(f"{len(bad)} left out (fix them in the answer files, then import again):")
        print("\n".join("  " + b for b in bad))


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
    elif cmd == "new" and len(sys.argv) > 2 and re.fullmatch(r"[a-z]{2,3}(_[A-Z]{2})?", sys.argv[2]):
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
        total = len(entries_of(text)) - 1
        for po in sorted(LOCALE.glob("*.po")):
            done = len(i18n.parse_po(po.read_text()))
            print(f"{po.stem}: {done} of {total} translated ({100 * done // max(total, 1)} %)")
        if not list(LOCALE.glob("*.po")):
            print("no translations yet")
    elif cmd == "export" and len(sys.argv) > 3:
        size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 150
        export(sys.argv[2], Path(sys.argv[3]), size, "--all" in sys.argv)
    elif cmd == "import" and len(sys.argv) == 4:
        import_(sys.argv[2], Path(sys.argv[3]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
