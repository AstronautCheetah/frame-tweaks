#!/usr/bin/env python3
"""Docs consistency: every tweak in components.tsv has a row in README.md, README links only
to tweaks that exist, and relative links in all Markdown files point at real files."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
ids = [l.split("\t")[0] for l in (root / "components.tsv").read_text().splitlines()
       if l.strip() and not l.startswith("#")]
readme = (root / "README.md").read_text()
rows = set(re.findall(r"^\|[^|]*\| \[\*\*[^]]+\*\*\]\(([a-z0-9-]+)/\)", readme, re.M))
problems = [f"README.md: no row for '{i}'" for i in ids if i not in rows]
problems += [f"README.md: row for unknown tweak '{r}'" for r in rows - set(ids)]
for md in root.rglob("*.md"):
    if ".git" in md.parts or "tmp" in md.relative_to(root).parts:
        continue
    text = re.sub(r"```.*?```", "", md.read_text(), flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)                # code isn't a link
    for target in re.findall(r"\]\((?!https?:|mailto:|#)([^)#\s]+)", text):
        if not (md.parent / target).exists():
            problems.append(f"{md.relative_to(root)}: broken link {target}")
print("\n".join(problems) or "docs ok")
sys.exit(1 if problems else 0)
