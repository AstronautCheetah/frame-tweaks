#!/usr/bin/env python3
"""For maintainers: move a pin to upstream's newest version, so a bump the weekly upstream check
(dev/check-upstream.sh) reports is one command plus review, not hand-editing URLs and hashes.

  dev/bump-pin.py TWEAK[/NAME]...     packs/official/<tweak>/pin, or <tweak>/<name>.pin (e.g. speech/voice)
  dev/bump-pin.py python              lib/python-constraints.txt to PyPI's newest

For each pin it finds the newest version the way dev/check-pins.sh does (GitHub release, git
commit, Hugging Face revision, rustup), downloads the file, writes the new version, URL and
sha256 (computed here, never taken from upstream's word alone; cross-checked against a
published <file>.sha256 when there is one) and the name of Frame Tweaks' copy (mirror=; upload it
with dev/mirror-pins.sh), and prints what to read before committing: the
changes upstream made. Nothing is committed; test, then commit the change like any other."""
import hashlib
import json
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "frame-tweaks-bump-pin"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode()


def sha256_of(url):
    h = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "frame-tweaks-bump-pin"})
    with urllib.request.urlopen(req, timeout=900) as r, tempfile.TemporaryFile() as f:
        while chunk := r.read(1 << 20):
            h.update(chunk)
            f.write(chunk)
    digest = h.hexdigest()
    try:                                       # a published checksum next to it (rustup has one)
        theirs = get(url + ".sha256").split()[0]
        if theirs != digest:
            sys.exit(f"{url}: downloaded file's sha256 {digest} differs from the published {theirs}")
    except Exception:
        pass
    return digest


def read_pin(path):
    return dict(l.split("=", 1) for l in path.read_text().splitlines() if "=" in l and not l.startswith("#"))


def write_pin(path, changes):
    lines = []
    for line in path.read_text().splitlines():
        k = line.split("=", 1)[0]
        lines.append(f"{k}={changes[k]}" if "=" in line and not line.startswith("#") and k in changes else line)
    path.write_text("\n".join(lines) + "\n")


def bump(path):
    p = read_pin(path)
    url, latest, cur = p["url"], p["latest"], p["version"]
    new, read = {}, ""
    if "static.rust-lang.org" in latest:                       # rustup, and the toolchain it installs
        v = re.search(r"^version = '(.*)'", get(latest), re.M)[1]
        new["version"], new["url"] = v, url.replace(f"/{cur}/", f"/{v}/")
        tc = re.search(r'^\[pkg\.rustc\]\nversion = "([0-9.]+)', get("https://static.rust-lang.org/dist/channel-rust-stable.toml"), re.M)[1]
        new["toolchain"] = tc
        read = f"https://github.com/rust-lang/rustup/blob/master/CHANGELOG.md, https://releases.rs (Rust {tc})"
    elif "huggingface.co" in latest:                           # a model repository's revision
        rev = json.loads(get(latest))["sha"]
        old = re.search(r"/resolve/([0-9a-f]{40})/", url)[1]
        new["url"] = url.replace(old, rev)
        new["version"] = rev[:len(cur)]
        repo = re.search(r"huggingface\.co/(.*?)/resolve/", url)[1]
        read = f"https://huggingface.co/{repo}/commits/main"
    elif "rev" in p:                                           # a git commit
        rev = json.loads(get(latest))["sha"]
        gh = re.search(r"github\.com/repos/([^/]+/[^/]+)/", latest)[1]
        new["rev"], new["url"] = rev, url.replace(p["rev"], rev)
        prefix = cur.split("+")[0]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", prefix):        # dated (Homebrew's installer)
            prefix = json.loads(get(latest))["commit"]["committer"]["date"][:10]
        else:                                                  # the crate's own version, if any
            try:
                prefix = re.search(r'^version = "(.*)"', get(f"https://raw.githubusercontent.com/{gh}/{rev}/Cargo.toml"), re.M)[1]
            except Exception:
                pass
        new["version"] = f"{prefix}+{rev[:7]}"
        read = f"https://github.com/{gh}/compare/{p['rev']}...{rev}"
    else:                                                      # a GitHub release
        tag = json.loads(get(latest))["tag_name"]
        v = tag.removeprefix("v")
        new["version"], new["url"] = v, url.replace(cur, v)
        gh = re.search(r"github\.com/repos/([^/]+/[^/]+)/", latest)[1]
        read = f"https://github.com/{gh}/releases/tag/{tag}"
    if new.get("url") == url and new.get("version") == cur:
        print(f"{path.relative_to(ROOT)}: already the newest ({cur})")
        return
    if "sha256" in p:
        print(f"{path.relative_to(ROOT)}: downloading {new['url']}")
        new["sha256"] = sha256_of(new["url"])
    if "mirror" in p:                                          # Frame Tweaks' copy: a new file name
        base = p["mirror"].rsplit("/", 1)[0]
        if "sha256" in p:
            new["mirror"] = f"{base}/{new['sha256'][:12]}-{new['url'].rsplit('/', 1)[1]}"
        else:
            new["mirror"] = f"{base}/{p['url'].rstrip('/').rsplit('/', 1)[1]}-{new['rev'][:7]}.tar.gz"
            new["mirror_sha256"] = ""
    write_pin(path, new)
    print(f"{path.relative_to(ROOT)}: {cur} -> {new['version']}" + (" (the file is unchanged)" if "sha256" in p and new["sha256"] == p["sha256"] else ""))
    print(f"  read before committing: {read}")
    if "mirror" in p:
        print("  then upload Frame Tweaks' copy: dev/mirror-pins.sh")


def bump_python():
    path = ROOT / "lib/python-constraints.txt"
    out = []
    for line in path.read_text().splitlines():
        m = re.fullmatch(r"([A-Za-z0-9_.-]+)==(.+)", line)
        if m:
            v = json.loads(get(f"https://pypi.org/pypi/{m[1]}/json"))["info"]["version"]
            if v != m[2]:
                print(f"{m[1]}: {m[2]} -> {v}  (https://pypi.org/project/{m[1]}/{v}/)")
            line = f"{m[1]}=={v}"
        out.append(line)
    path.write_text("\n".join(out) + "\n")


def main(args):
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    for a in args:
        if a == "python":
            bump_python()
            continue
        tweak, _, name = a.partition("/")
        path = ROOT / "packs/official" / tweak / (f"{name}.pin" if name else "pin")
        if not path.is_file():
            sys.exit(f"no pin {path.relative_to(ROOT)}")
        bump(path)
    print("Next: dev/check-pins.sh, the tests (python3 -m unittest discover -s tests; dev/test-tweaks.sh), "
          "a reinstall of the tweak on the Frame, then commit.")


if __name__ == "__main__":
    main(sys.argv[1:])
