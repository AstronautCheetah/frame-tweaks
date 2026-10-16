#!/usr/bin/env python3
"""For maintainers, and run daily by .github/workflows/linked.yml (which keeps one GitHub issue up
to date with the result): what changed in the projects Frame Tweaks links to (a manifest's link:,
docs/mods.md "Linking a project"). It runs their own installers and checks only that they're
installed, so their releases can change what a tweak's page says, or move the file its status
checks (Recline-VR 1.3 did). Prints a Markdown report; exits 1 if something needs attention.

  Needs attention: none of the files a link's installed: names is in the project's README any
  more (a release may have moved them: its status would read "not installed").
  Worth a look: a release newer than the one last looked at (lib/tested-versions, link-ID=TAG).
  Read its notes, check the link's commands and the tweak's page, then set the new tag there.

  dev/check-links.py          (GH_TOKEN, if set, for GitHub's API)
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import manifest  # noqa: E402


def get(url):
    """The body at url, or None when there's nothing there (404)."""
    headers = {"User-Agent": "frame-tweaks-check-links"}
    if url.startswith("https://api.github.com/"):
        headers["Accept"] = "application/vnd.github+json"
        if os.environ.get("GH_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GH_TOKEN']}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
            return r.read().decode()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def links():
    """(id, title, its manifest's link, the project's GitHub owner/name) for each linked tweak."""
    for readme in sorted(ROOT.glob("packs/*/*/README.md")):
        meta, _body = manifest.front_matter(readme.read_text())
        link = meta.get("link")
        if not link:
            continue
        where = " ".join(str(v) for v in ((meta.get("source") or {}).get("url"), link.get("readme")) if v)
        m = re.search(r"github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?(?:[/#]|\s|$)", where)
        yield readme.parent.name, meta.get("title", readme.parent.name), link, m[1] if m else None


def tested():
    lines = (ROOT / "lib/tested-versions").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))


def check(found, seen, get=get):
    """(red, yellow): what needs attention, and what's worth a look. found: links(); seen:
    tested()."""
    red, yellow = [], []
    for tid, title, link, repo in found:
        if not repo:
            yellow.append(f"**{title}** (`{tid}`): its project isn't on GitHub, so nothing here looks at it")
            continue
        try:
            release = get(f"https://api.github.com/repos/{repo}/releases/latest")
            readme = get(f"https://raw.githubusercontent.com/{repo}/HEAD/README.md")
        except (OSError, urllib.error.URLError) as e:
            yellow.append(f"**{title}**: couldn't reach [{repo}](https://github.com/{repo}) ({e})")
            continue
        paths = link["installed"] if isinstance(link["installed"], list) else [link["installed"]]
        if readme is not None and not any(p in readme or p.replace("~/", "$HOME/") in readme for p in paths):
            red.append(f"**{title}**: its [README](https://github.com/{repo}#readme) no longer names "
                       f"{', '.join(f'`{p}`' for p in paths)}, what `link.installed` checks: if a release "
                       "moved it, the status reads \"not installed\". Name a file it documents now.")
        if release:
            r = json.loads(release)
            tag, was = r["tag_name"], seen.get(f"link-{tid}")
            if tag != was:
                yellow.append(f"**{title}**: [{repo}](https://github.com/{repo}) **{tag}** is out "
                              f"({r['published_at'][:10]}; last looked at: {was or 'none'}). Read "
                              f"[its notes]({r['html_url']}), check `{tid}`'s link and page, then set "
                              f"`link-{tid}={tag}` in `lib/tested-versions`.")
    return red, yellow


def main():
    red, yellow = check(list(links()), tested())
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                         text=True).stdout.strip() or "this checkout"
    print(f"Checked {datetime.now(timezone.utc):%Y-%m-%d} against {sha}.")
    print()
    if not red and not yellow:
        print("All clear: every linked project's newest release has been looked at, and its README "
              "still names what its status checks.")
    if red:
        print("## 🔴 Needs attention\n")
        print("\n".join(f"- {line}" for line in red) + "\n")
    if yellow:
        print("## 🟡 Worth a look\n")
        print("\n".join(f"- {line}" for line in yellow) + "\n")
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
