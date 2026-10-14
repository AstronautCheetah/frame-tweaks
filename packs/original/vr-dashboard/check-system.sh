#!/bin/bash
# SteamVR internals the dashboard patches rely on.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
D="$HOME/.local/share/frame-tweaks/vr-dashboard/sft-dashboard"
[ -x "$D" ] || D="$(dirname "$0")/sft-dashboard"
r=$("$D" check) || { t 'SteamVR dashboard code changed (%s): those patches stay off' "$r"; echo; exit 1; }
[ -f "$HOME/.config/openvr/config/steamvr.vrsettings" ] || { t '%s not found' steamvr.vrsettings; echo; exit 1; }
t 'SteamVR dashboard code as expected'; echo
