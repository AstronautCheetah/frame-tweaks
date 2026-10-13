#!/bin/bash
# Big scroll strips beside windows (vr-dashboard). The desktop scrolls through its Remote Desktop
# portal (KDE asks once); other windows with arrow keys (ydotool).
source "$(dirname "$0")/../lib/common.sh"
# Windows other than the desktop scroll with arrow keys through ydotool.
[ -x "$BIN/ydotool" ] || "$REPO_DIR/ydotool/install.sh"
mkdir -p "$HOME/.local/state/frame-tweaks"
# Settings (the installer window edits them; kept on uninstall).
[ -f "$HOME/.config/frame-tweaks/scroll-strips.json" ] || {
    mkdir -p "$HOME/.config/frame-tweaks"
    echo '{"vertical": "right", "horizontal": "top", "thickness": 0.04}' > "$HOME/.config/frame-tweaks/scroll-strips.json"
}
install_dashboard_patch scroll-strips "$REPO_DIR/scroll-strips/patch.js"
