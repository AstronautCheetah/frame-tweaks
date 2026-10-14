#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
if [ -x "$BIN/nordvpn-wg" ]; then "$BIN/nordvpn-wg" down >/dev/null 2>&1 || true; fi
nmcli -t -f TYPE,NAME connection show | sed -n "s/^wireguard:\(NordVPN .*\)/\1/p" | while read -r c; do nmcli connection delete "$c" >/dev/null && say "removed connection $c"; done
pkill -f "^$QT_VENV/bin/python $BIN/nordvpn-tray" 2>/dev/null || true
restore_kconfig nordvpn
remove_files "$ICONS/256x256/apps/frame-tweaks-nordvpn.png" "$BIN/nordvpn-wg" "$BIN/nordvpn-tray" "$APPS/nordvpn-tray.desktop" "$HOME/.config/autostart/nordvpn-tray.desktop" "$HOME/.config/nordvpn-wg"
# The PyQt6 venv is shared with Arrow Pad and Screen snip: only the last one removes it.
[ -x "$BIN/arrowpad" ] || [ -x "$BIN/frame-snip" ] || remove_files "$QT_VENV"
