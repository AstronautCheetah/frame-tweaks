#!/bin/bash
# Bluetooth headphones, music only: a WirePlumber setting that leaves out the call profiles.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
CONF="$HOME/.config/wireplumber/wireplumber.conf.d/90-frame-tweaks-bt-music-only.conf"

# An unchanged file is left alone: a reinstall (after a README edit, say) that rewrote it would make
# it newer than the running WirePlumber, and status.sh would then say it isn't in force yet.
if cmp -s "$TWEAK_DIR/bt-music-only.conf" "$CONF"; then
    say "$(t 'Bluetooth headphones connect for music only (A2DP)')"
    exit 0
fi
write_file "$CONF" < "$TWEAK_DIR/bt-music-only.conf"
# WirePlumber reads its configuration as it starts. Restarting it while SteamVR runs would
# restart Valve's VR audio compositor (a WirePlumber module) under SteamVR, so then it waits.
if pgrep -x vrserver >/dev/null; then
    say "$(t "Installed; applies when the Frame restarts (SteamVR is using the sound system now).")"
elif sysctl_user restart wireplumber 2>/dev/null; then
    say "$(t 'Bluetooth headphones now connect for music only (A2DP). Reconnect ones connected already.')"
else
    say "$(t 'Installed; applies when the Frame restarts.')"
fi
