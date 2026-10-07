#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
if [ -x "$BIN/nordvpn-wg" ]; then "$BIN/nordvpn-wg" down >/dev/null 2>&1 || true; fi
nmcli -t -f TYPE,NAME connection show | sed -n "s/^wireguard:\(NordVPN .*\)/\1/p" | while read -r c; do nmcli connection delete "$c" >/dev/null && say "removed connection $c"; done
pkill -f "^$QT_VENV/bin/python $BIN/nordvpn-tray" 2>/dev/null || true
remove_files "$BIN/nordvpn-wg" "$BIN/nordvpn-tray" "$APPS/nordvpn-tray.desktop" "$HOME/.config/autostart/nordvpn-tray.desktop" "$HOME/.config/nordvpn-wg"
[ -x "$BIN/arrowpad" ] || remove_files "$QT_VENV"
