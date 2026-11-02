#!/usr/bin/env python3
"""Docs consistency: every tweak in the official packs has a row in docs/tweaks.md and a link in
README.md's overview, both name only tweaks that exist, relative links in all Markdown files point
at real files, and links to a table in docs/tweaks.md (#convenience) at one of its headings."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
ids = [d.name for pack in ("core", "integrations", "third-party") for d in (root / "packs" / pack).iterdir() if (d / "README.md").is_file()]


def read(path):
    return (root / path).read_text() if (root / path).is_file() else ""


def anchor(heading):
    """The anchor GitHub gives a heading (as dev/gen-docs.py makes the overview's links)."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


TWEAK = r"(?:\.\./)?packs/(?:core|integrations|third-party)/([a-z0-9-]+)/\)"
tables = read("docs/tweaks.md")
overview = re.search(r"<!-- generated:overview .*?<!-- /generated:overview -->", read("README.md"), re.S)
found = {"docs/tweaks.md": set(re.findall(r"^\|[^|]*\| \[\*\*[^]]+\*\*\]\(" + TWEAK, tables, re.M)),
         "README.md": set(re.findall(r"\]\(" + TWEAK, overview[0] if overview else ""))}
problems = []
for page, named in found.items():
    problems += [f"{page}: no entry for '{i}'" for i in ids if i not in named]
    problems += [f"{page}: unknown tweak '{r}'" for r in named - set(ids)]
headings = {anchor(h) for h in re.findall(r"^#+ (.*)", tables, re.M)}
for md in root.rglob("*.md"):
    parts = md.relative_to(root).parts
    if {".git", "tmp", "references"} & set(parts):
        continue
    if parts[0] == "packs" and len(parts) > 2 and parts[1] not in ("core", "integrations", "third-party"):
        continue                    # (a local pack, not published: packs/attic, say)
    text = re.sub(r"```.*?```", "", md.read_text(), flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)                # code isn't a link
    links = re.findall(r"\]\((?!https?:|mailto:|#)([^)#\s]+)", text)
    links += re.findall(r"""<(?:img|a|source)\b[^>]*?\s(?:src|href)=["'](?!https?:|mailto:|#|data:)([^"'#]+)""", text)  # (HTML)
    for target in links:
        if not (md.parent / target).exists():
            problems.append(f"{md.relative_to(root)}: broken link {target}")
    for target, frag in re.findall(r"\]\((?!https?:)([^)#\s]*tweaks\.md)#([^)\s]+)\)", text):
        if (md.parent / target).resolve() == (root / "docs/tweaks.md").resolve() and frag not in headings:
            problems.append(f"{md.relative_to(root)}: no heading for {target}#{frag}")
print("\n".join(problems) or "docs ok")
sys.exit(1 if problems else 0)
