#!/usr/bin/env bash
# For maintainers: put Frame Tweaks' own copy of each pinned download (a pin's mirror= line) on
# this repo's "mirror" release, so installs keep working if upstream deletes or changes a file
# (lib/common.sh fetch_pinned falls back to it, checked against the pin's sha256). Uploads only
# what's missing, each checked against its pin first. A pinned git commit (clipboard) becomes a
# source archive, whose sha256 this writes into the pin's mirror_sha256= (commit that change).
# Pins that can't be copied say why in nomirror=. Needs gh, signed in.
#   dev/mirror-pins.sh            upload what's missing, refresh the release notes
#   dev/mirror-pins.sh --check    list what's missing (exit 1 if anything is)
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1
TAG=mirror
check=; [ "${1:-}" = --check ] && check=1
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
val() { sed -n "s/^$1=//p" "$2"; }

notes() {
    echo "Frame Tweaks' copies of the upstream files its tweaks pin. Installs use one only when"
    echo "upstream's file is gone or changed, and only after checking it against the SHA256 in its"
    echo "pin. Each file keeps its upstream licence:"
    echo
    for pin in packs/*/*/pin packs/*/*/*.pin; do
        [ -n "$(val mirror "$pin")" ] || continue
        echo "- \`$(basename "$(val mirror "$pin")")\` (\`$pin\`, from $(val url "$pin")): $(val license "$pin")"
    done
}

if ! have=$(gh release view "$TAG" --json assets --jq '.assets[].name' 2>/dev/null); then
    [ -z "$check" ] || { echo "no \"$TAG\" release yet"; exit 1; }
    gh release create "$TAG" --prerelease --title "Mirror of pinned downloads" --notes "$(notes)" \
        --target "$(git rev-parse HEAD)"
    have=""
fi
missing=0
for pin in packs/*/*/pin packs/*/*/*.pin; do
    m=$(val mirror "$pin"); [ -n "$m" ] || continue
    name=$(basename "$m")
    grep -qxF "$name" <<<"$have" && continue
    missing=1
    if [ -n "$check" ]; then echo "not mirrored: $pin ($name)"; continue; fi
    url=$(val url "$pin"); sha=$(val sha256 "$pin"); rev=$(val rev "$pin")
    if [ -n "$sha" ]; then
        curl -fL# -o "$work/$name" "$url"
        echo "$sha  $work/$name" | sha256sum -c --quiet - ||
            { echo "$pin: upstream's file differs from the pin; not uploading it" >&2; exit 1; }
    else                                   # a git commit: its source, as an archive
        git clone -q "$url" "$work/src"
        git -C "$work/src" archive --format=tar.gz --prefix="${name%.tar.gz}/" "$rev" > "$work/$name"
        rm -rf "$work/src"
        new=$(sha256sum "$work/$name" | cut -c1-64)
        if [ "$new" != "$(val mirror_sha256 "$pin")" ]; then
            sed -i "s/^mirror_sha256=.*/mirror_sha256=$new/" "$pin"
            echo "$pin: mirror_sha256 written; commit it"
        fi
    fi
    gh release upload "$TAG" "$work/$name"
    rm -f "$work/$name"
done
if [ -n "$check" ]; then exit "$missing"; fi
gh release edit "$TAG" --notes "$(notes)" >/dev/null
echo "mirror: up to date"
