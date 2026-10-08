#!/usr/bin/env bash
# For maintainers: compare each <tweak>/pin with upstream's latest release. To bump a pin,
# read the release notes and diff, then update version, url and sha256 (the sha256 from the
# release's SHA256SUMS, or computed from the downloaded file) in one reviewed commit.
set -euo pipefail
cd "$(dirname "$0")/.."
for pin in */pin; do
    id=${pin%/pin}
    cur=$(sed -n 's/^version=//p' "$pin")
    api=$(sed -n 's/^latest=//p' "$pin")
    tag=$(curl -fsSL --max-time 10 "$api" | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | sed -n 1p) || tag=""
    latest=${tag#v}
    if [ -z "$latest" ]; then
        echo "$id: pinned $cur; couldn't reach upstream"
    elif [ "$latest" = "$cur" ]; then
        echo "$id: pinned $cur (latest)"
    else
        echo "$id: pinned $cur; upstream has $latest ($(dirname "$api" | sed 's|api.github.com/repos|github.com|')/tag/$tag)"
    fi
done
