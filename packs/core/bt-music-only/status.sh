#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
CONF="$HOME/.config/wireplumber/wireplumber.conf.d/90-frame-tweaks-bt-music-only.conf"
[ -f "$CONF" ] || status_missing "$(t 'not installed')"
# WirePlumber reads its configuration as it starts: a file written since then isn't in force.
# (ActiveEnterTimestampMonotonic: microseconds since boot; 0 or empty when it isn't running.)
started=$(sysctl_user show wireplumber -p ActiveEnterTimestampMonotonic --value 2>/dev/null) || started=
if [ -n "$started" ] && [ "$started" != 0 ]; then
    boot=$(awk -v now="$(date +%s)" '{printf "%d", now - $1}' /proc/uptime)
    [ "$(stat -c %Y "$CONF")" -gt $((boot + started / 1000000)) ] &&
        status_warn "$(t "Applies when WirePlumber restarts: restart the Frame, or ↻ Reinstall with SteamVR closed")"
fi
# (a device connected before the setting took effect keeps the profiles it was given)
if command -v pactl >/dev/null && pactl list cards 2>/dev/null | grep -q 'headset-head-unit'; then
    status_warn "$(t "A connected device still offers its call profile: reconnect it, or restart the Frame")"
fi
status_ok "$(t 'Bluetooth headphones connect for music only (A2DP)')"
