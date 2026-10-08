#!/usr/bin/env python3
"""Generate the docs that list tweaks, from each tweak's `meta` file (and components.tsv order):

  README.md       the Core / Extras / Helpers tables
  SECURITY.md     the "What each tweak changes on your system" rows
  <tweak>/README  an "At a glance" box (survives updates, what it changes, how to undo)

Generated parts sit between <!-- generated:NAME --> and <!-- /generated:NAME --> markers.
  dev/gen-docs.py           rewrite them
  dev/gen-docs.py --check   fail if anything is out of date (CI)"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = ("emoji", "name", "group", "what", "why", "changes", "access", "survives-updates", "undo")


def tweaks():
    ids = [l.split("\t")[0] for l in (ROOT / "components.tsv").read_text().splitlines()
           if l.strip() and not l.startswith("#")]
    out = []
    for i in ids:
        meta = {}
        for line in (ROOT / i / "meta").read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        missing = [k for k in KEYS if not meta.get(k)]
        if missing:
            sys.exit(f"{i}/meta: missing {', '.join(missing)}")
        if meta["group"] not in ("core", "extras", "helper"):
            sys.exit(f"{i}/meta: group must be core, extras or helper")
        out.append((i, meta))
    return out


def link(i, name):
    """[**Claude Code**](claude-code/) (command line): bold name, plain parenthetical."""
    m = re.match(r"(.*?)( \(.*\))?$", name)
    return f"[**{m[1]}**]({i}/){m[2] or ''}"


def readme_table(rows, group):
    lines = ["| | Tweak | What you get | Why (on the Frame) |", "|---|---|---|---|"]
    lines += [f"| {m['emoji']} | {link(i, m['name'])} | {m['what']} | {m['why']} |"
              for i, m in rows if m["group"] == group]
    return "\n".join(lines)


def security_rows(rows):
    return "\n".join(f"| {i} | {m['changes']} | {m['access']} |" for i, m in rows)


def glance(m):
    lines = ["> **At a glance**", ">",
             f"> - **Survives SteamOS updates:** {m['survives-updates']}",
             f"> - **Changes:** {m['changes']}"]
    if m["access"] not in ("–", "-"):
        lines.append(f"> - **Unusual access:** {m['access']}")
    lines.append(f"> - **Undo:** {m['undo']}")
    return "\n".join(lines)


def put(text, name, body, path):
    begin, end = f"<!-- generated:{name} (dev/gen-docs.py, from each tweak's meta) -->", f"<!-- /generated:{name} -->"
    block = f"{begin}\n{body}\n{end}"
    pat = re.compile(re.escape(begin.split(" (")[0]) + r".*?" + re.escape(end), re.S)
    if pat.search(text):
        return pat.sub(lambda _: block, text)
    if name == "glance":          # first run: after the title and first paragraph
        parts = text.split("\n\n", 2)
        return "\n\n".join(parts[:2] + [block] + parts[2:]) if len(parts) == 3 else text + "\n\n" + block + "\n"
    sys.exit(f"{path}: no {begin.split(' (')[0]} marker")


def main():
    check = "--check" in sys.argv
    rows = tweaks()
    targets = {ROOT / "README.md": [(g, readme_table(rows, g)) for g in ("core", "extras", "helper")],
               ROOT / "SECURITY.md": [("security", security_rows(rows))]}
    for i, m in rows:
        targets[ROOT / i / "README.md"] = [("glance", glance(m))]
    stale = []
    for path, parts in targets.items():
        old = path.read_text()
        new = old
        for name, body in parts:
            new = put(new, name, body, path)
        if new != old:
            stale.append(str(path.relative_to(ROOT)))
            if not check:
                path.write_text(new)
    if check and stale:
        sys.exit("out of date (run dev/gen-docs.py): " + ", ".join(stale))
    print("docs up to date" if not stale else "updated: " + ", ".join(stale))


if __name__ == "__main__":
    main()
