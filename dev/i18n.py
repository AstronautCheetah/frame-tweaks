#!/usr/bin/env python3
"""Translations (gettext .po files in locale/; lib/i18n.py reads them; locale/README.md).

  dev/i18n.py extract      write locale/frame-tweaks.pot: every text marked in the code
                           (_("..."), ngettext, pgettext) and the official tweaks' manifest text
  dev/i18n.py check        fail if the .pot is out of date (CI)
  dev/i18n.py new LANG     start locale/LANG.po from the .pot (LANG: de, pt_BR, …)
  dev/i18n.py update       bring every locale/*.po up to date with the .pot (translations kept;
                           new text untranslated; removed text kept as #~ comments)
  dev/i18n.py stats        how much of each language is translated"""
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
CODE = sorted([*ROOT.glob("gui/*.py"), ROOT / "gui/frame-tweaks-gui.py", *ROOT.glob("lib/*.py")])
FUNCS = {"_": ("msgid",), "ngettext": ("msgid", "msgid_plural"), "pgettext": ("msgctxt", "msgid")}


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
    for source in (from_code(), from_manifests()):
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


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    text = template()
    if cmd == "extract":
        LOCALE.mkdir(exist_ok=True)
        POT.write_text(text + "\n")
        print(f"{POT.relative_to(ROOT)}: {len(entries_of(text)) - 1} texts")
    elif cmd == "check":
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
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
