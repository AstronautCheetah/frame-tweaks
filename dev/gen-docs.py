#!/usr/bin/env python3
"""Generate the docs that list tweaks, from the official pack (packs/official: each tweak's
README.md front matter, in pack.md's order):

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
sys.path.insert(0, str(ROOT / "lib"))
import sft  # noqa: E402
OFFICIAL = "packs/official"


def tweaks():
    out = []
    for d in sft.read_pack(ROOT / OFFICIAL)[1]:
        c, problems = sft.read_tweak(d)
        if not c:
            sys.exit("\n".join(problems))
        out.append((c["id"], {"emoji": c["emoji"], "name": c["title"], "group": c["tier"], "what": c["what"],
                              "why": c["why"], "changes": c["changes"], "access": c["access"],
                              "survives-updates": c["survives_updates"], "undo": c["undo"],
                              "experimental": c["experimental"]}))
    return out


def link(i, name):
    """[**Claude Code**](packs/official/claude-code/) (command line): bold name, plain parenthetical."""
    m = re.match(r"(.*?)( \(.*\))?$", name)
    return f"[**{m[1]}**]({OFFICIAL}/{i}/){m[2] or ''}"


def readme_table(rows, group):
    lines = ["| | Tweak | What you get | Why (on the Frame) |", "|---|---|---|---|"]
    lines += [f"| {m['emoji']} | {link(i, m['name'])}{' 🧪' if m.get('experimental') else ''} | {m['what']} | {m['why']} |"
              for i, m in rows if m["group"] == group]
    return "\n".join(lines)


def security_rows(rows):
    return "\n".join(f"| {i} | {m['changes']} | {m['access']} |" for i, m in rows)


def glance(m):
    lines = ["> **At a glance**", ">",
             f"> - **Survives SteamOS updates:** {m['survives-updates']}",
             f"> - **Changes:** {m['changes']}"]
    if m.get("experimental"):
        lines.append(f"> - **🧪 Experimental:** {m['experimental']}")
    if m["access"] not in ("–", "-"):
        lines.append(f"> - **Unusual access:** {m['access']}")
    lines.append(f"> - **Undo:** {m['undo']}")
    return "\n".join(lines)


def put(text, name, body, path):
    begin, end = f"<!-- generated:{name} (dev/gen-docs.py, from each tweak's README front matter) -->", f"<!-- /generated:{name} -->"
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
        targets[ROOT / OFFICIAL / i / "README.md"] = [("glance", glance(m))]
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
