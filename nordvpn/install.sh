#!/bin/bash
# NordVPN (NordLynx/WireGuard) as NetworkManager connections that survive SteamOS updates.
source "$(dirname "$0")/../lib/common.sh"
ensure_path
ensure_tweaks_venv
install_py_tool "$REPO_DIR/nordvpn/nordvpn-wg"

# Tray icon (SteamOS has no Plasma network applet). PyQt6 venv shared with arrowpad.
QT_VENV="$HOME/.local/share/arrowpad/venv"
if ! "$QT_VENV/bin/python" -c 'import PyQt6' 2>/dev/null; then
    say "Creating Python venv with PyQt6 (~280 MB, shared with arrowpad)"
    python3 -m venv "$QT_VENV"
    "$QT_VENV/bin/pip" install -q -c "$REPO_DIR/lib/python-constraints.txt" PyQt6
fi
sed "1s|.*|#!$QT_VENV/bin/python|" "$REPO_DIR/nordvpn/nordvpn-tray" > "$BIN/nordvpn-tray"
chmod 755 "$BIN/nordvpn-tray"
install_icon frame-tweaks-nordvpn
install_desktop "$REPO_DIR/nordvpn/nordvpn-tray.desktop"
mkdir -p "$HOME/.config/autostart"
sed "s|@BIN@|$BIN|g" "$REPO_DIR/nordvpn/nordvpn-tray.desktop" > "$HOME/.config/autostart/nordvpn-tray.desktop"

say "Installed. Now run:  nordvpn-wg setup   (asks for your NordVPN access token once)"
say "The tray icon starts with desktop mode (or launch 'NordVPN Tray' now)."
