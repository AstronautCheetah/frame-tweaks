#!/usr/bin/env bash
# dev/update-check.sh: checks that updates keep working, on a Frame: before and after an update of
# this Frame's own install, and for every release, that copies installed at earlier releases
# update to it. Only reads Frame Tweaks and the tweaks; it writes its own folder.
#   dev/update-check.sh snapshot LABEL      record this Frame's install as it is now (version,
#                                           signatures, each tweak's status, user services, the
#                                           programs in ~/.local/bin, the last installer logs, a
#                                           debug report, a git bundle of the checkout)
#   dev/update-check.sh compare A B         what changed between two snapshots (names or paths;
#                                           part of a name will do)
#   dev/update-check.sh release-test [ORIGIN] [N]
#                                           copies installed from GitHub at each of the last N
#                                           releases (4 unless given) update, in throwaway homes,
#                                           as ./install.sh update does: each must verify the
#                                           newest release's signature and move to it. ORIGIN
#                                           (GitHub unless given) is where they update from: a
#                                           local copy tries a release before it's pushed
#   dev/update-check.sh list                the snapshots so far
# Snapshots go to $FRAME_TWEAKS_CHECKS (~/frame-update-checks unless set)/snapshots, and are
# copied to the microSD card when one is mounted, so they outlast the headset.
set -uo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
BASE=${FRAME_TWEAKS_CHECKS:-$HOME/frame-update-checks}
SNAPS=$BASE/snapshots
GITHUB=https://github.com/AstronautCheetah/frame-tweaks
RELEASE='^v[0-9]+\.[0-9]+\.[0-9]+$'

nocolor() { sed -E 's/\x1b\[[0-9;]*[A-Za-z]//g'; }
card() {
    local d
    for d in /run/media/"$USER"/*/; do mountpoint -q "$d" 2>/dev/null && { echo "${d%/}"; return; }; done
}
releases() { git "$@" tag -l 'v*' | grep -E "$RELEASE" | sort -V; }

snapshot() {
    local label=${1:?"snapshot needs a label, e.g. before-update"} out f t x signers c
    out=$SNAPS/$(date +%Y%m%d-%H%M%S)-$label
    mkdir -p "$out"
    {   date --iso-8601=seconds
        # shellcheck disable=SC1091   # (the system's)
        . /etc/os-release; echo "SteamOS ${VERSION_ID:-?} build ${BUILD_ID:-?}"
        echo "branch: $(steamos-select-branch -c 2>/dev/null | tail -1)"
        uname -r
    } > "$out/system.txt"
    {   echo "version: $(cd "$REPO" && ./install.sh version 2>&1 | tail -1)"
        echo "checkout: $(git -C "$REPO" symbolic-ref -q --short HEAD || echo "detached (a release install)")"
        echo "HEAD: $(git -C "$REPO" rev-parse HEAD)"
        echo "tags at HEAD: $(git -C "$REPO" tag --points-at HEAD | tr '\n' ' ')"
        echo "origin: $(git -C "$REPO" remote get-url origin)"
        echo "== local changes"; git -C "$REPO" status --short
        echo "== commits not on origin"; git -C "$REPO" log --oneline '@{upstream}..HEAD' 2>/dev/null
    } > "$out/git.txt" 2>&1
    git -C "$REPO" for-each-ref --format='%(objectname) %(*objectname) %(refname)' refs/remotes refs/tags > "$out/refs.txt"
    # Each recent release's signature, checked against the signers it lists itself (one signed by
    # the key before shows as such: the updater accepts it through the release that hands on).
    signers=$(mktemp)
    for t in $(releases -C "$REPO" | tail -6); do
        git -C "$REPO" show "refs/tags/$t:dev/release-signers" > "$signers" 2>/dev/null
        for x in "$t" "cosign-$t"; do
            git -C "$REPO" rev-parse -q --verify "refs/tags/$x" >/dev/null || continue
            if git -C "$REPO" -c gpg.ssh.allowedSignersFile="$signers" verify-tag "$x" >/dev/null 2>&1; then f=good
            else f="not by the keys it lists (signed by the key before)"; fi
            echo "$x -> $(git -C "$REPO" rev-parse --short "refs/tags/$x^{commit}"): $f"
        done
    done > "$out/signatures.txt"
    rm -f "$signers"
    (cd "$REPO" && ./install.sh status 2>&1 | nocolor) > "$out/status.txt"
    for f in "$HOME"/.local/state/frame-tweaks/installed/*; do [ -f "$f" ] && echo "${f##*/} $(cat "$f")"; done > "$out/installed.txt"
    {   systemctl --user list-unit-files --no-pager --no-legend 2>/dev/null |
            grep -iE 'frame|tweak|wallet|clipboard|ydotool|arrow|snip|speech|nordvpn|dictat|dashboard|app-timers|charge'
        echo "== failed"; systemctl --user --failed --no-pager --no-legend 2>/dev/null
    } > "$out/units.txt"
    (cd "$HOME/.local/bin" 2>/dev/null && find . -maxdepth 1 -type f -print0 | sort -z | xargs -0 -r sha256sum) > "$out/bin.sha256"
    find "$HOME/.local/state/frame-tweaks/logs" -maxdepth 1 -name '[0-9]*.log' -printf '%T@ %p\n' 2>/dev/null |
        sort -rn | head -3 | cut -d' ' -f2- | xargs -r cp -t "$out/"
    (cd "$REPO" && ./install.sh debug-info 2>&1 | nocolor | tail -3) > "$out/debug-info.txt"
    git -C "$REPO" bundle create "$out/checkout.bundle" --all >/dev/null 2>&1   # (every commit and tag, to go back to)
    c=$(card)
    if [ -n "$c" ]; then mkdir -p "$c/frame-update-checks" && cp -r "$out" "$c/frame-update-checks/" && sync; fi
    echo "snapshot: $out${c:+ (copied to $c/frame-update-checks)}"
    echo "  tweaks OK: $(grep -c '✔' "$out/status.txt")"
    grep -E '^ *(!|✘|✖)' "$out/status.txt" | sed 's/^/  attention: /'
}

find_snapshot() {
    if [ -d "$1" ]; then echo "$1"; return; fi
    find "$SNAPS" -mindepth 1 -maxdepth 1 -type d -name "*$1*" 2>/dev/null | sort | tail -1
}

compare() {
    local a b f
    a=$(find_snapshot "${1:?compare A B}"); b=$(find_snapshot "${2:?compare A B}")
    [ -d "$a" ] && [ -d "$b" ] || { echo "no such snapshot: $1 or $2 (dev/update-check.sh list)" >&2; return 1; }
    echo "comparing ${a##*/} -> ${b##*/}"
    for f in system.txt git.txt signatures.txt status.txt installed.txt units.txt bin.sha256; do
        # (the first line of system.txt is when the snapshot was taken)
        if ! cmp -s <(grep -v '^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]T' "$a/$f") <(grep -v '^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]T' "$b/$f"); then
            echo "== $f"
            diff <(grep -v '^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]T' "$a/$f") <(grep -v '^20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]T' "$b/$f") | grep '^[<>]'
        fi
    done
    echo "(refs.txt changes whenever a branch or tag moves; diff it yourself when that matters)"
}

release_test() {
    local origin=${1:-$GITHUB} n=${2:-4} tmp pass=0 fail=0 start home out rc head want newest log
    tmp=$(mktemp -d /tmp/frame-tweaks-release-test.XXXX)
    git clone -q --mirror "$GITHUB" "$tmp/installed-from.git" || { echo "can't reach GitHub" >&2; rm -rf "$tmp"; return 1; }
    newest=$(git ls-remote --tags "$origin" 'v*' | sed 's#.*refs/tags/##; /\^{}$/d' | grep -E "$RELEASE" | sort -V | tail -1)
    [ -n "$newest" ] || { echo "no release found at $origin" >&2; rm -rf "$tmp"; return 1; }
    echo "updating to $newest from $origin"
    for start in $(releases --git-dir="$tmp/installed-from.git" | tail -"$n"); do
        home=$tmp/home-$start
        mkdir -p "$home"
        git clone -q "$tmp/installed-from.git" "$home/frame-tweaks" &&
            git -C "$home/frame-tweaks" -c advice.detachedHead=false checkout -q "refs/tags/$start"
        git -C "$home/frame-tweaks" remote set-url origin "$origin"
        out=$(cd "$home/frame-tweaks" && HOME=$home XDG_CONFIG_HOME=$home/.config XDG_DATA_HOME=$home/.local/share \
              XDG_STATE_HOME=$home/.local/state timeout 300 nice -n 19 ./install.sh update 2>&1 | nocolor)
        rc=$?
        head=$(git -C "$home/frame-tweaks" rev-parse --short HEAD)
        want=$(git -C "$home/frame-tweaks" rev-parse -q --short --verify "refs/tags/$newest^{commit}")
        if [ -n "$want" ] && [ "$head" = "$want" ] && grep -q 'signature verified' <<<"$out"; then
            echo "PASS $start -> $newest ($head)"; pass=$((pass + 1))
        else
            mkdir -p "$BASE"
            log=$BASE/release-test-$start-$(date +%Y%m%d-%H%M%S).log
            printf '%s\n' "$out" > "$log"
            echo "FAIL $start: exit $rc, at $head, not $newest (${want:-not fetched}); its output: $log"
            grep -iE 'signature|signed|release|error|fatal|failed' <<<"$out" | head -5 | sed 's/^/    /'
            fail=$((fail + 1))
        fi
    done
    rm -rf "$tmp"
    echo "$pass passed, $fail failed"
    [ "$fail" -eq 0 ]
}

case ${1:-} in
    snapshot) shift; mkdir -p "$SNAPS"; snapshot "$@" ;;
    compare) shift; compare "$@" ;;
    release-test) shift; release_test "$@" ;;
    list) ls -1 "$SNAPS" 2>/dev/null ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//' ;;
    *) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2 ;;
esac
