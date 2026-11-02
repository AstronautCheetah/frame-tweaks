#!/usr/bin/env bash
# For maintainers: add a test record to steam-frame.yml (its tested: list, which frame-commons'
# COMPAT.md is built from), read from the Frame it was tested on: the headset's SteamOS version
# and build, SteamVR's version and the update channel. Run it after trying a release on a Frame.
#
#   dev/record-tested.sh [--print] HOST RESULT "NOTES"
#     HOST     the Frame, as ssh reaches it ("." on the Frame itself)
#     RESULT   works, partial or broken (a broken record is as useful as a works one)
#     NOTES    one short line: which release, and what was tried
#     --print  print the record instead of adding it
set -euo pipefail
cd "$(dirname "$0")/.."
print=
[ "${1:-}" = --print ] && { print=1; shift; }
[ $# = 3 ] || { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
host=$1 result=$2 notes=$3
case $result in works|partial|broken) ;; *) echo "RESULT: works, partial or broken" >&2; exit 2 ;; esac
# (the spec's notes are one short line, quoted: no quote or newline that would break it)
[[ $notes != *[\"$'\n']* ]] && [ ${#notes} -le 120 ] || { echo "NOTES: one line, at most 120 characters, no \"" >&2; exit 2; }
read_frame() {
    # SteamOS's own version (the headset's 0.x line) and build; SteamVR's version as vrserver logs it
    # when it starts (its version.txt is a build number); the channel steamos-select-branch is on.
    grep -E '^(VERSION_ID|BUILD_ID)=' /etc/os-release
    echo "STEAMVR=$(grep -m1 -oE 'vrserver [0-9][0-9.]* startup' "${FRAME_TWEAKS_VRSERVER_LOG:-$HOME/.local/share/Steam/logs/vrserver.txt}" 2>/dev/null | cut -d' ' -f2)"
    echo "CHANNEL=$(steamos-select-branch -c 2>/dev/null || true)"
}
# shellcheck disable=SC2029   # (on purpose: read_frame's definition is sent, to run there)
if [ "$host" = . ]; then facts=$(read_frame); else facts=$(ssh "$host" "$(declare -f read_frame); read_frame"); fi
get() { sed -n "s/^$1=//p" <<<"$facts" | tr -d '"' | head -1; }
steamos=$(get VERSION_ID) build=$(get BUILD_ID) steamvr=$(get STEAMVR) channel=$(get CHANNEL)
[ -n "$steamos" ] || { echo "couldn't read the headset's SteamOS version" >&2; exit 1; }
case $channel in rel|stable) channel=stable ;; beta|preview) ;; main) channel=preview ;; *) channel= ;; esac
rec="  - { steamos: \"$steamos\""
[ -z "$build" ] || rec+=", build: \"$build\""
[ -z "$steamvr" ] || rec+=", steamvr: \"$steamvr\""
[ -z "$channel" ] || rec+=", channel: $channel"
rec+=", date: $(date -u +%F), result: $result, notes: \"$notes\" }"
if [ -n "$print" ]; then echo "$rec"; else echo "$rec" >> steam-frame.yml; echo "added: $rec"; fi
