#!/usr/bin/env bash
# For maintainers: compare pinned upstream versions with what upstream has now.
#  - <tweak>/pin with a release tag (latest= GitHub releases API), a git commit (rev=, latest=
#    commits API) or a Hugging Face revision (latest= .../revision/main)
#  - lib/python-constraints.txt against PyPI
# To bump: read the release notes / diff, then update the pin (version, url, sha256 or rev) in
# one reviewed commit. The sha256 comes from the release's SHA256SUMS, Hugging Face's file
# listing, or the downloaded file.
set -euo pipefail
cd "$(dirname "$0")/.."
for pin in packs/*/*/pin packs/*/*/*.pin; do
    [ -f "$pin" ] || continue
    id=${pin#packs/*/}; id=${id%/pin}; id=${id%.pin}
    cur=$(sed -n 's/^version=//p' "$pin"); api=$(sed -n 's/^latest=//p' "$pin")
    json=$(curl -fsSL --max-time 15 "$api" 2>/dev/null) || { echo "$id: pinned $cur; couldn't reach upstream"; continue; }
    if grep -q '^rev=' "$pin" && [[ $api != */releases/* ]]; then    # git commit (else: a release's)
        new=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["sha"])' <<<"$json")
        [ "$new" = "$(sed -n 's/^rev=//p' "$pin")" ] && echo "$id: pinned $cur (latest commit)" ||
            echo "$id: pinned $cur; upstream HEAD is ${new:0:7}"
    elif [[ $api == *static.rust-lang.org* ]]; then     # rustup, and the Rust toolchain it installs
        new=$(sed -n "s/^version = '\(.*\)'/\1/p" <<<"$json")
        [ "$new" = "$cur" ] && echo "$id: rustup $cur (latest)" || echo "$id: rustup $cur; upstream has $new"
        tc=$(curl -fsSL --max-time 15 https://static.rust-lang.org/dist/channel-rust-stable.toml 2>/dev/null |
             grep -A1 '^\[pkg.rustc\]' | sed -n 's/^version = "\([0-9.]*\).*/\1/p')
        pinned=$(sed -n 's/^toolchain=//p' "$pin")
        [ "$tc" = "$pinned" ] && echo "$id: Rust $pinned (latest stable)" || echo "$id: Rust $pinned; stable is ${tc:-?}"
    elif [[ $api == *huggingface.co* ]]; then           # model repository revision
        new=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["sha"])' <<<"$json")
        if [[ $new == "$cur"* ]]; then echo "$id: pinned $cur (latest revision)"
        else   # the repository moved on; has our file? (big files: their sha256 is in a header)
            url=$(sed -n 's/^url=//p' "$pin"); main=${url/\/resolve\/$cur\//\/resolve\/main\/}
            sha=$(curl -fsSIL --max-time 15 "$main" | tr -d '\r"' | sed -n 's/^x-linked-etag: *\([0-9a-f]\{64\}\)$/\1/Ip' | tail -1)
            [ -n "$sha" ] || sha=$(curl -fsSL --max-time 60 "$main" | sha256sum | cut -c1-64)
            [ "$sha" = "$(sed -n 's/^sha256=//p' "$pin")" ] && echo "$id: pinned ${cur:0:8} (the file is unchanged at ${new:0:8})" ||
                echo "$id: pinned ${cur:0:8}; the file changed at ${new:0:8}"
        fi
    else                                               # GitHub release
        tag=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])' <<<"$json"); latest=${tag#v}
        [ "$latest" = "$cur" ] && echo "$id: pinned $cur (latest)" || echo "$id: pinned $cur; upstream has $latest"
    fi
done
while IFS='=' read -r pkg ver; do
    [[ -z $pkg || $pkg == \#* ]] && continue
    pkg=${pkg%=}
    new=$(curl -fsSL --max-time 15 "https://pypi.org/pypi/$pkg/json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])') || new="?"
    [ "$new" = "$ver" ] && echo "pypi $pkg: pinned $ver (latest)" || echo "pypi $pkg: pinned $ver; PyPI has $new"
done < <(sed 's/==/=/' lib/python-constraints.txt)
