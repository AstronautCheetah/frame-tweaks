#!/usr/bin/env bash
# For maintainers, and run weekly by .github/workflows/upstream.yml (which keeps one GitHub issue
# up to date with the result): what outside the repo has changed or gone away. Prints a Markdown
# report; exits 1 if something needs attention.
#
#  Needs attention (installs would fail, or a feature would switch itself off):
#   - a pinned download (<tweak>/pin, <tweak>/*.pin) is gone, or no longer matches its sha256;
#     a pinned git commit is gone (installs then use Frame Tweaks' copy, if it has one)
#   - Frame Tweaks' copy of a pinned download (mirror=) is missing from the "mirror" release
#   - an Arch Linux ARM package we install is gone, or its new build needs a newer glibc or
#     libstdc++ than SteamOS has (lib/tested-versions)
#   - Homebrew's scrcpy moved to a major version phone-touch wasn't tested with
#  Worth a look (newer versions to test and bump; nothing breaks meanwhile):
#   - dev/check-pins.sh's newer pins and Python packages
#   - scrcpy, android-tools or ydotool newer than lib/tested-versions
#
#   dev/check-upstream.sh            everything (downloads the pinned files: ~400 MB)
#   dev/check-upstream.sh --quick    pinned files: only that they're still there
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
quick=; [ "${1:-}" = --quick ] && quick=1
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
red=() yellow=()
tested() { sed -n "s/^$1=//p" lib/tested-versions; }

# fetch <url> <out>: 0 ok; prints "gone" (404/410) or "unreachable" otherwise
fetch() {
    local code
    code=$(curl -sSL --retry 3 --retry-all-errors --max-time 900 -o "$2" -w '%{http_code}' "$1" 2>/dev/null)
    [ "$code" = 200 ] && return 0
    case $code in 404|410) echo gone ;; *) echo "unreachable (HTTP ${code:-none})" ;; esac
    return 1
}

# ---- pinned downloads ----
for pin in packs/*/*/pin packs/*/*/*.pin; do
    [ -f "$pin" ] || continue
    url=$(sed -n 's/^url=//p' "$pin"); sha=$(sed -n 's/^sha256=//p' "$pin"); rev=$(sed -n 's/^rev=//p' "$pin")
    if [ -n "$sha" ]; then
        if [ -n "$quick" ]; then
            curl -fsSIL --retry 3 --max-time 60 -o /dev/null "$url" 2>/dev/null || red+=("\`$pin\`: $url can't be fetched")
        elif why=$(fetch "$url" "$work/f"); then
            got=$(sha256sum "$work/f" | cut -c1-64)
            [ "$got" = "$sha" ] || red+=("\`$pin\`: $url changed (sha256 now $got); installs refuse it")
        else
            red+=("\`$pin\`: $url is $why")
        fi
        rm -f "$work/f"
    elif [ -n "$rev" ]; then                       # a git commit (built from source)
        g="$work/git"; rm -rf "$g"; git init -q "$g"
        git -C "$g" fetch -q --depth 1 "$url" "$rev" 2>/dev/null || red+=("\`$pin\`: commit ${rev:0:7} is gone from $url")
    fi
done

# ---- Frame Tweaks' copies (the "mirror" release; dev/mirror-pins.sh) ----
if assets=$(timeout 60 gh release view mirror --json assets --jq '.assets[].name' 2>/dev/null); then
    for pin in packs/*/*/pin packs/*/*/*.pin; do
        m=$(sed -n 's/^mirror=//p' "$pin"); [ -n "$m" ] || continue
        grep -qxF "$(basename "$m")" <<<"$assets" ||
            red+=("\`$pin\`: Frame Tweaks' copy (\`$(basename "$m")\`) isn't on the mirror release: run \`dev/mirror-pins.sh\`")
    done
else
    yellow+=("Couldn't list the mirror release's files (gh not signed in, or no release yet)")
fi

# ---- Arch Linux ARM: still there, and still runs on SteamOS's libraries ----
mirror=$(sed -n 's/^ALARM_MIRROR="${ALARM_MIRROR:-\(.*\)}"$/\1/p' lib/common.sh)
glibc=$(tested steamos-glibc); glibcxx=$(tested steamos-glibcxx)
declare -A listing
newest() {   # newest <repo> <name>: file name of the newest package
    [ -n "${listing[$1]:-}" ] || listing[$1]=$(curl -fsSL --retry 3 --max-time 60 "$mirror/$1/")
    grep -oE "\"$2-[0-9][^\"/]*-aarch64\.pkg\.tar\.(xz|zst)\"" <<<"${listing[$1]}" | tr -d '"' | sort -V | tail -1
}
# (the packages adb-scrcpy/install.sh and ydotool/install.sh fetch)
for p in "extra android-tools" "extra protobuf" "extra fmt" "extra abseil-cpp" "core libusb" "extra ydotool"; do
    read -r repo name <<<"$p"
    file=$(newest "$repo" "$name")
    [ -n "$file" ] || { red+=("Arch Linux ARM: package \`$name\` is gone from $repo"); continue; }
    ver=${file#"$name"-}; ver=${ver%-aarch64.pkg.tar.*}
    want=$(tested "$name")
    [ -z "$want" ] || [ "$ver" = "$want" ] || yellow+=("Arch Linux ARM \`$name\` is now $ver (tested: $want)")
    d="$work/pkg-$name"; mkdir -p "$d"
    if why=$(fetch "$mirror/$repo/$file" "$d.pkg"); then
        bsdtar -xf "$d.pkg" -C "$d" usr 2>/dev/null
        need=$(find "$d" -type f -exec readelf -V --wide {} + 2>/dev/null | grep -oE 'GLIBC(XX)?_[0-9.]+' | sort -u)
        top=$(grep '^GLIBC_' <<<"$need" | sed 's/GLIBC_//' | sort -V | tail -1)
        topxx=$(grep '^GLIBCXX_' <<<"$need" | sed 's/GLIBCXX_//' | sort -V | tail -1)
        newer() { [ -n "$1" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)" != "$2" ]; }
        newer "$top" "$glibc" && red+=("Arch Linux ARM \`$name\` $ver needs glibc $top; SteamOS has $glibc (installs keep the copy you have; new installs fail)")
        newer "$topxx" "$glibcxx" && red+=("Arch Linux ARM \`$name\` $ver needs libstdc++ GLIBCXX_$topxx; SteamOS has $glibcxx")
    else
        red+=("Arch Linux ARM \`$file\` is $why")
    fi
    rm -rf "$d" "$d.pkg"
done

# ---- Homebrew's scrcpy (phone-touch speaks its control protocol) ----
want=$(tested scrcpy)
have=$(curl -fsSL --retry 3 --max-time 60 https://formulae.brew.sh/api/formula/scrcpy.json |
       python3 -c 'import json,sys; print(json.load(sys.stdin)["versions"]["stable"])' 2>/dev/null)
if [ -z "$have" ]; then
    yellow+=("Homebrew's scrcpy version couldn't be read")
elif [ "${have%%.*}" != "${want%%.*}" ]; then
    red+=("Homebrew's scrcpy is now $have (tested: $want): the mirror's VR extras switch themselves off until \`SCRCPY_TESTED\` in adb-scrcpy/phone-touch is updated")
elif [ "$have" != "$want" ]; then
    yellow+=("Homebrew's scrcpy is now $have (tested: $want)")
fi

# ---- newer pins and Python packages ----
pins=$(dev/check-pins.sh 2>&1); rc=$?
while IFS= read -r line; do
    case $line in *"upstream has"*|*"HEAD is"*|*"PyPI has"*|*"stable is"*|*"file changed"*|*"couldn't reach"*)
        yellow+=("$line") ;; esac
done <<<"$pins"
# (it stops at its first error: what it didn't get to is missing above)
[ "$rc" = 0 ] || yellow+=("\`dev/check-pins.sh\` stopped early (exit $rc), so newer versions may be missing here: run it by hand")

# ---- report ----
echo "Checked $(date -u '+%Y-%m-%d') against $(git rev-parse --short HEAD 2>/dev/null || echo 'this checkout')."
echo
if [ ${#red[@]} -eq 0 ] && [ ${#yellow[@]} -eq 0 ]; then
    echo "All clear: every pinned download is there and unchanged; nothing newer upstream."
fi
if [ ${#red[@]} -gt 0 ]; then
    echo "## 🔴 Needs attention"; echo
    printf -- '- %s\n' "${red[@]}"; echo
fi
if [ ${#yellow[@]} -gt 0 ]; then
    echo "## 🟡 Worth a look"; echo
    printf -- '- %s\n' "${yellow[@]}"; echo
    echo "Bump a pin with \`dev/bump-pin.py <tweak>\` (it downloads, checksums and rewrites the pin; review upstream's changes first), then test and commit."
fi
[ ${#red[@]} -eq 0 ]
