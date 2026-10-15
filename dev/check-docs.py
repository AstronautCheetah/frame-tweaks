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
    parts = md.relative_to(root).parts
    if {".git", "tmp", "references"} & set(parts):
        continue
    if parts[0] == "packs" and len(parts) > 2 and parts[1] not in ("original", "integrations", "third-party"):
        continue                    # (a local pack, not published: packs/attic, say)
    text = re.sub(r"```.*?```", "", md.read_text(), flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)                # code isn't a link
    links = re.findall(r"\]\((?!https?:|mailto:|#)([^)#\s]+)", text)
    links += re.findall(r"""<(?:img|a|source)\b[^>]*?\s(?:src|href)=["'](?!https?:|mailto:|#|data:)([^"'#]+)""", text)  # (HTML)
    for target in links:
        if not (md.parent / target).exists():
            problems.append(f"{md.relative_to(root)}: broken link {target}")
print("\n".join(problems) or "docs ok")
sys.exit(1 if problems else 0)
