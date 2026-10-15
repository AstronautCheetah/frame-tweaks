#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# A reinstall (↻, FRAME_TWEAKS_REINSTALL) only replaces the programs: it keeps the connections
# and doesn't disconnect. Your key and locations (~/.config/nordvpn-wg, which would take a new
# access token to set up again) are its settings: kept, or removed by ./install.sh uninstall as
# the ⚙ Preferences say.
keep=${FRAME_TWEAKS_REINSTALL:-}
if [ -z "$keep" ]; then
    if [ -x "$BIN/nordvpn-wg" ]; then "$BIN/nordvpn-wg" down >/dev/null 2>&1 || true; fi
    # (nmcli reports one that won't go, and the uninstall goes on: with `&&` last in the loop, the
    # last connection failing stopped it here, at every try)
    nmcli -t -f TYPE,NAME connection show | sed -n "s/^wireguard:\(NordVPN .*\)/\1/p" | while read -r c; do
        if nmcli connection delete "$c" >/dev/null; then say "$(t 'removed connection %s' "$c")"; fi
    done
fi
pkill -f "^$QT_VENV/bin/python $BIN/nordvpn-tray" 2>/dev/null || true
restore_kconfig nordvpn
remove_icon frame-tweaks-nordvpn
remove_desktop nordvpn-tray.desktop
remove_files "$BIN/nordvpn-wg" "$BIN/nordvpn-tray" "$HOME/.config/autostart/nordvpn-tray.desktop"
# The PyQt6 venv is shared with Arrow Pad, Screen snip and the installer window.
remove_qt_venv
