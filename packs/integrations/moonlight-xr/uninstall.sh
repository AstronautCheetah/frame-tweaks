#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
HOME_DIR="$HOME/Games/MoonlightXRNative"
if [ -f "$HOME_DIR/.frame-tweaks-dock_icon.py" ]; then
    python3 "$HOME_DIR/.frame-tweaks-dock_icon.py" remove "$HOME_DIR/app" || true
fi
remove_desktop moonlight-xr.desktop
rm -rf "$HOME_DIR"
say "$(t 'Kept your settings and pairing in %s. Remove its Steam library entry in Steam (Manage, Remove non-Steam game from your library), and unpair the Frame in Sunshine.' "$HOME/.config/moonlight-xr")"
