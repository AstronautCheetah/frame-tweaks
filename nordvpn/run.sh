#!/bin/bash
# label: Tray
source "$(dirname "$0")/../lib/common.sh"
if pgrep -f "nordvpn-tray" >/dev/null; then
    notify-send -a NordVPN "NordVPN tray is running" "$("$BIN/nordvpn-wg" status 2>/dev/null | sed -n 1p)"
else
    exec gtk-launch nordvpn-tray
fi
