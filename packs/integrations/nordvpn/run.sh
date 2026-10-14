#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# (The tray program itself, not anything that merely mentions it.)
if pgrep -u "$(id -u)" -f "python[^ ]* $BIN/nordvpn-tray\$" >/dev/null; then
    notify-send -a NordVPN "$(t 'NordVPN tray is running')" "$("$BIN/nordvpn-wg" status 2>/dev/null | sed -n 1p)"
else
    exec gtk-launch nordvpn-tray
fi
