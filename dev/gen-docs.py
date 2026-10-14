#!/usr/bin/env python3
"""Generate the docs that list tweaks, from the official packs (packs/original,
packs/integrations, then packs/third-party: each tweak's README.md front matter, in their pack.md's order):

  README.md       a table of tweaks per category, in the installer window's order
  SECURITY.md     the "What each tweak changes on your system" rows
  <tweak>/README  its opening (what it is, why on a Steam Frame), a "What it changes" section
                  (survives updates, what it changes, unusual access, how to undo), and
                  for a tweak that installs another project, that project's own README at the end
                  (from <tweak>/upstream.md; dev/fetch-upstream-readmes.py updates it)

Generated parts sit between <!-- generated:NAME --> and <!-- /generated:NAME --> markers.
  dev/gen-docs.py           rewrite them
  dev/gen-docs.py --check   fail if anything is out of date (CI)"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import sft  # noqa: E402


def tweaks():
    out = []
    for d in (d for pack in sft.OFFICIAL_PACKS for d in sft.read_pack(pack)[1]):
        c, problems = sft.read_tweak(d)
        if not c:
            sys.exit("\n".join(problems))
        out.append((c["id"], {"dir": d.relative_to(ROOT).as_posix(), "emoji": c["emoji"], "name": c["title"], "group": c["tier"], "what": c["what"],
                              "why": c["why"], "changes": c["changes"], "access": c["access"],
                              "survives-updates": c["survives_updates"], "undo": c["undo"],
                              "experimental": c["experimental"], "upstream": c["upstream_readme"],
                              "category": c["category"]}))
    return out


def link(m):
    """[**Claude Code**](packs/integrations/claude-code/) (command line): bold name, plain parenthetical."""
    n = re.match(r"(.*?)( \(.*\))?$", m["name"])
    return f"[**{n[1]}**]({m['dir']}/){n[2] or ''}"


def readme_tables(rows):
    """One table per category, in pack.md's order (as the installer window lists them)."""
    order = sft.read_pack(sft.ORIGINAL)[0]["categories"]
    cats = order + sorted({m["category"] for _, m in rows} - set(order))
    out = []
    for cat in cats:
        mine = [(i, m) for i, m in rows if m["category"] == cat]
        if not mine:
            continue
        out += [f"### {cat}", "", "| | Tweak | What you get | Why on a Steam Frame |", "|---|---|---|---|"]
        out += [f"| {m['emoji']} | {link(m)}{' 🧪' if m.get('experimental') else ''}"
                f"{' *(helper)*' if m['group'] == 'helper' and 'helper' not in m['name'].lower() else ''} | {m['what']} | {m['why']} |" for i, m in mine]
        out.append("")
    return "\n".join(out).rstrip()


def security_rows(rows):
    return "\n".join(f"| {i} | {m['changes']} | {m['access']} |" for i, m in rows)


def intro(m):
    return f"{m['what']}\n\n**Why on a Steam Frame:** {m['why']}"


def changes(m):
    lines = ["## What it changes", "",
             f"- **Survives SteamOS updates:** {m['survives-updates']}",
             f"- **Changes:** {m['changes']}"]
    if m.get("experimental"):
        lines.append(f"- **🧪 Experimental:** {m['experimental']}")
    if m["access"] not in ("–", "-", "None"):
        lines.append(f"- **Unusual access:** {m['access']}")
    lines.append(f"- **Undo:** {m['undo']}")
    return "\n".join(lines)


def licence(m):
    """The project's licence, as its pin names it (license=, license_file=): "[MIT](url)", or one
    link per licence of a choice ("[MIT](…) or [Apache-2.0](…)")."""
    f = ROOT / m["dir"] / "pin"
    pin = dict(line.split("=", 1) for line in f.read_text().splitlines() if "=" in line) if f.is_file() else {}
    if not (pin.get("license") and pin.get("license_file")):
        return "its own licence"
    names, urls = pin["license"].split(" (")[0].split(" or "), pin["license_file"].split()
    return " or ".join(f"[{n}]({u})" for n, u in zip(names, urls)) if len(names) == len(urls) else \
        f"[{' or '.join(names)}]({urls[0]})"


def upstream(i, m):
    """The installed project's own README, after a footer line (whose it is, and its licence: a
    copy carries its copyright and licence) and a separator."""
    owner, repo, ref = m["upstream"].split("/")[3:6]
    copy = ROOT / m["dir"] / "upstream.md"
    if not copy.is_file():
        sys.exit(f"{copy.relative_to(ROOT)} is missing: run dev/fetch-upstream-readmes.py {i}")
    return (f"---\n\n*The rest of this page is [{owner}/{repo}](https://github.com/{owner}/{repo})'s own "
            f"README at `{ref[:12]}`, © its authors, under {licence(m)}, as its author wrote it (only links "
            f"and heading levels adjusted), included for its instructions and credits. Everything above "
            f"is Frame Tweaks'.*\n\n" + copy.read_text().strip())


def put(text, name, body, path):
    source = "upstream.md" if name == "upstream" else "each tweak's README front matter"
    begin, end = f"<!-- generated:{name} (dev/gen-docs.py, from {source}) -->", f"<!-- /generated:{name} -->"
    block = f"{begin}\n{body}\n{end}"
    pat = re.compile(re.escape(begin.split(" (")[0]) + r".*?" + re.escape(end), re.S)
    if body is None:              # no longer generated (upstream_readme: removed): the old block goes
        return re.sub(r"\n*" + pat.pattern + r"\n?", "\n", text, flags=re.S) if pat.search(text) else text
    if pat.search(text):
        return pat.sub(lambda _: block, text)
    if name == "upstream":        # first run: at the end
        return text.rstrip("\n") + "\n\n" + block + "\n"
    if name == "intro":           # first run: right after the title
        m = re.search(r"^# .*\n", text, re.M)
        return text[:m.end()] + "\n" + block + "\n" + text[m.end():] if m else block + "\n\n" + text
    if name == "changes":         # first run: before Credits, else before the Check/Remove footer
        for anchor in ("\n## Credits", "\n---\nCheck:"):
            if anchor in text:
                i = text.index(anchor)
                return text[:i].rstrip("\n") + "\n\n" + block + "\n" + text[i:]
        return text.rstrip("\n") + "\n\n" + block + "\n"
    sys.exit(f"{path}: no {begin.split(' (')[0]} marker")


def main():
    check = "--check" in sys.argv
    rows = tweaks()
    targets = {ROOT / "README.md": [("tweaks", readme_tables(rows))],
               ROOT / "SECURITY.md": [("security", security_rows(rows))]}
    for i, m in rows:
        targets[ROOT / m["dir"] / "README.md"] = [("intro", intro(m)), ("changes", changes(m)),
                                                  ("upstream", upstream(i, m) if m["upstream"] else None)]
    stale = []
    for path, parts in targets.items():
        old = path.read_text()
        # (The "At a glance" box became the "What it changes" section, further down.)
        new = re.sub(r"\n?<!-- generated:glance .*?<!-- /generated:glance -->\n?", "\n", old, flags=re.S)
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
