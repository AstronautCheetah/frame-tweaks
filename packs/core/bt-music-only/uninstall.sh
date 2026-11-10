#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
CONF="$HOME/.config/wireplumber/wireplumber.conf.d/90-frame-tweaks-bt-music-only.conf"

remove_files "$CONF"
# (as in install.sh: not under SteamVR)
if pgrep -x vrserver >/dev/null; then
    say "$(t "The call profiles are back when the Frame restarts (SteamVR is using the sound system now).")"
elif sysctl_user restart wireplumber 2>/dev/null; then
    say "$(t 'The call profiles are back; reconnect headphones connected already.')"
else
    say "$(t 'The call profiles are back when the Frame restarts.')"
fi
