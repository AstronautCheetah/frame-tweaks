#!/bin/bash
# VR memory guard: desktop apps leave memory free for SteamVR, Firefox has a limit of its own, and
# SteamVR is the last thing the kernel stops when memory runs out. Limits in
# ~/.config/frame-tweaks/vr-memory-guard.conf; see README.md.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
CONF="$HOME/.config/frame-tweaks/vr-memory-guard.conf"
MEMINFO=${FRAME_TWEAKS_MEMINFO:-/proc/meminfo}
UNITS="$HOME/.config/systemd/user"
DROPIN=frame-tweaks-vr-memory-guard.conf
mkdir -p "${CONF%/*}"
[ -f "$CONF" ] || install -m644 "$TWEAK_DIR/vr-memory-guard.conf" "$CONF"

get() { sed -n "s/^$1=//p" "$CONF" | tail -1 | tr -d '[:space:]'; }
# mib SIZE: a size written as 5G or 512M (or 0) in MiB; fails on anything else.
mib() {
    case $1 in
        0) echo 0 ;;
        [1-9]*[Gg]) [[ ${1%?} =~ ^[0-9]+$ ]] && echo $(( ${1%?} * 1024 )) ;;
        [1-9]*[Mm]) [[ ${1%?} =~ ^[0-9]+$ ]] && echo "${1%?}" ;;
        *) return 1 ;;
    esac
}
size() {     # size NAME: the setting in MiB, or stop and say which line is wrong
    local v; v=$(mib "$(get "$1")") && [ -n "$v" ] ||
        die "$(t '%s in %s should be a size such as 5G or 512M (it is "%s").' "$1" "$CONF" "$(get "$1")")"
    echo "$v"
}
reserve=$(size reserve_for_vr); apps_swap=$(size apps_swap_max)
ff=$(size firefox_max); ff_swap=$(size firefox_swap_max)
total=$(awk '/^MemTotal:/ {print int($2 / 1024)}' "$MEMINFO")
[ -n "$total" ] && [ "$total" -gt 0 ] || die "$(t "Can't read how much memory this device has (%s)." "$MEMINFO")"
apps=$(( total - reserve ))
# (Less than 2 GB for every desktop app together would stop them constantly.)
[ "$apps" -ge 2048 ] || die "$(t 'reserve_for_vr (%s) leaves less than 2 GB of the %s MB for desktop apps: make it smaller in %s.' "$(get reserve_for_vr)" "$total" "$CONF")"
[ "$ff" -le "$apps" ] || warn "$(t 'firefox_max is more than all desktop apps together may use (%s MB): the apps limit applies first.' "$apps")"

# dropin UNIT TEXT: our drop-in for UNIT (a real unit, or a prefix such as app-flatpak-X-.scope,
# which systemd applies to every unit whose name starts with it).
dropin() { mkdir -p "$UNITS/$1.d"; printf '%s\n' "$2" > "$UNITS/$1.d/$DROPIN"; }
# MemoryMax without MemoryHigh: an app over its limit is stopped at once. With MemoryHigh the
# kernel throttles it instead, which on the Frame left a runaway app crawling for minutes rather
# than stopped. MemorySwapMax: without it the app goes on growing in swap.
dropin app.slice "[Slice]
MemoryMax=${apps}M
MemorySwapMax=${apps_swap}M"
dropin app-flatpak-org.mozilla.firefox-.scope "[Scope]
MemoryMax=${ff}M
MemorySwapMax=${ff_swap}M"
# (100 is the lowest a user's own service may set, the user manager's own value; apps run at 200,
# so when memory runs out anyway the kernel stops an app before SteamVR.)
dropin steamvr.service "[Service]
OOMScoreAdjust=100"
sysctl_user daemon-reload || true

# The drop-ins apply when each unit starts; set the running ones too, until the next login. (A
# running slice doesn't take a new drop-in on daemon-reload.)
sysctl_user set-property --runtime app.slice MemoryMax="${apps}M" MemorySwapMax="${apps_swap}M" ||
    warn "$(t "Couldn't set the apps' limit now; it applies at your next login.")"
for scope in $(sysctl_user list-units --type=scope --state=running --plain --no-legend 'app-flatpak-org.mozilla.firefox-*.scope' 2>/dev/null | awk '{print $1}'); do
    sysctl_user set-property --runtime "$scope" MemoryMax="${ff}M" MemorySwapMax="${ff_swap}M" || true
done
say "$(t 'Desktop apps together: up to %s MB (%s MB kept for VR); Firefox: up to %s MB.' "$apps" "$reserve" "$ff")"
if sysctl_user is-active --quiet steamvr.service; then
    say "$(t 'SteamVR is stopped last from its next start.')"
fi
