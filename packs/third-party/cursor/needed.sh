#!/bin/bash
# Needed only while desktop mode's pointer doesn't show in VR. From gamescope 3.16.30 (SteamOS
# 0.5.6, the beta in October 2026) SteamVR draws it (gamescope 865e0c1), and this fix leaves a
# second pointer, a black X, on top. Exit 1 with why when this Frame doesn't need it.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
v=$(pacman -Q gamescope 2>/dev/null | awk '{print $2}' || true)      # (none: offered)
# (version order without its release, -1: sort -V, which every system has, unlike vercmp)
[ -n "$v" ] && [ "$(printf '%s\n' 3.16.30 "${v%-*}" | sort -V | head -1)" = 3.16.30 ] || exit 0
echo "$(t 'SteamOS shows the pointer itself since gamescope 3.16.30 (this Frame has %s)' "$v")"
exit 1
