#!/usr/bin/env python3
"""For maintainers: copy the README of each project an official tweak installs (its manifest's
upstream_readme:, at the version the tweak pins) into <tweak>/upstream.md, with its pictures
in <tweak>/upstream/, so dev/gen-docs.py can show it below the tweak's own README (on GitHub and
on the installer window's details page, which can't load pictures from the web).

  dev/fetch-upstream-readmes.py [TWEAK...]     all tweaks with upstream_readme:, or these

Relative links become links to the file on GitHub at that version; headings move one level
down (theirs sit under ours). Run it again after bumping the tweak's pin, review, commit.

Only https:// from GitHub is fetched (github_url; redirects too): the README is someone else's,
and a picture of file:///home/you/.config/gh/hosts.yml, say, was read and saved here, to be
committed. Any other picture stays a link to it, with a warning."""
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import sft  # noqa: E402

MAX_PICTURE = 2_000_000          # bigger pictures stay links


def github_url(url):
    """url is https:// on GitHub: github.com or one of its user-content hosts (raw files, and
    uploaded pictures and where they redirect: raw., user-images., private-user-images., camo., …),
    with no user, password or port of its own."""
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or "").lower()
    return (u.scheme == "https" and u.netloc.lower() == host
            and (host == "github.com" or host.endswith(".githubusercontent.com")))


class GitHubOnly(urllib.request.HTTPRedirectHandler):
    """Redirects followed only to github_url."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not github_url(newurl):
            raise urllib.error.HTTPError(newurl, code, f"redirected away from GitHub: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# Only HTTPS: urlopen's opener also reads file:, ftp: and data: addresses.
OPENER = urllib.request.OpenerDirector()
for handler in (urllib.request.HTTPSHandler(), GitHubOnly(), urllib.request.HTTPDefaultErrorHandler(),
                urllib.request.HTTPErrorProcessor(), urllib.request.UnknownHandler()):
    OPENER.add_handler(handler)


def get(url):
    if not github_url(url):
        raise OSError(f"not https:// from GitHub: {url}")
    with OPENER.open(urllib.request.Request(url, headers={"User-Agent": "frame-tweaks"}), timeout=60) as r:
        return r.read()


def convert(text, raw_url, out):
    owner, repo, ref, path = re.match(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)", raw_url).groups()
    base = posix_dir = path.rsplit("/", 1)[0] + "/" if "/" in path else ""
    blob = f"https://github.com/{owner}/{repo}/blob/{ref}/"
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/"
    kept = {}

    def picture(src, alt):
        full = src if re.match(r"https?://", src) else urllib.parse.urljoin(raw + base, src)
        if not github_url(full):
            print(f"  left as a link (not https:// from GitHub): {full}", file=sys.stderr)
            return f"![{alt}]({full})"
        name = re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.unquote(full.rsplit("/", 1)[-1].split("?")[0])) or "picture"
        if name not in kept:
            try:
                data = get(full)
            except OSError:
                return f"![{alt}]({full})"
            if len(data) > MAX_PICTURE:
                return f"[{alt or name}]({full})"
            (out / name).write_bytes(data)
            kept[name] = True
        return f"![{alt}](upstream/{name})"

    lines, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced:
            if line.startswith("#"):
                line = "#" + line
            line = re.sub(r'<img\b[^>]*?\bsrc="([^"]+)"[^>]*?(?:\balt="([^"]*)")?[^>]*>',
                          lambda m: picture(m[1], m[2] or ""), line)
            line = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: picture(m[2], m[1]), line)
            line = re.sub(r"(?<!!)\[([^\]]+)\]\((?!https?:|#|mailto:|upstream/)([^)\s]+)\)",
                          lambda m: f"[{m[1]}]({urllib.parse.urljoin(blob + posix_dir, m[2])})", line)
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def main():
    want = set(sys.argv[1:])
    for d in (d for pack in sft.OFFICIAL_PACKS for d in sft.read_pack(pack)[1]):
        c, problems = sft.read_tweak(d)
        if not c or not c["upstream_readme"] or (want and c["id"] not in want):
            continue
        out = d / "upstream"
        if out.is_dir():
            for old in out.iterdir():
                old.unlink()
        out.mkdir(exist_ok=True)
        text = get(c["upstream_readme"]).decode("utf-8", "replace")
        (d / "upstream.md").write_text(convert(text, c["upstream_readme"], out))
        pictures = len(list(out.iterdir()))
        if not pictures:
            out.rmdir()
        print(f"{c['id']}: {c['upstream_readme']} -> {(d / 'upstream.md').relative_to(ROOT)} ({pictures} pictures)")
    print("Now run dev/gen-docs.py, review the changes, commit.")


if __name__ == "__main__":
    main()
