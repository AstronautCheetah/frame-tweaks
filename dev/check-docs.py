#!/usr/bin/env python3
"""Docs consistency: every tweak in the official packs has a row in README.md, README links only
to tweaks that exist, and relative links in all Markdown files point at real files."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
ids = [d.name for pack in ("original", "integrations", "third-party") for d in (root / "packs" / pack).iterdir() if (d / "README.md").is_file()]
readme = (root / "README.md").read_text()
rows = set(re.findall(r"^\|[^|]*\| \[\*\*[^]]+\*\*\]\(packs/(?:original|integrations|third-party)/([a-z0-9-]+)/\)", readme, re.M))
problems = [f"README.md: no row for '{i}'" for i in ids if i not in rows]
problems += [f"README.md: row for unknown tweak '{r}'" for r in rows - set(ids)]
for md in root.rglob("*.md"):
    if {".git", "tmp", "references"} & set(md.relative_to(root).parts):
        continue
    text = re.sub(r"```.*?```", "", md.read_text(), flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)                # code isn't a link
    for target in re.findall(r"\]\((?!https?:|mailto:|#)([^)#\s]+)", text):
        if not (md.parent / target).exists():
            problems.append(f"{md.relative_to(root)}: broken link {target}")
print("\n".join(problems) or "docs ok")
sys.exit(1 if problems else 0)
