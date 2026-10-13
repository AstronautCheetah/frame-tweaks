#!/bin/bash
# Big scroll strips beside floating windows (vr-dashboard; scrolling via ydotool).
source "$(dirname "$0")/../lib/common.sh"
# Scrolling goes through ydotool's virtual mouse wheel.
[ -x "$BIN/ydotool" ] || "$REPO_DIR/ydotool/install.sh"
# Settings (the installer window edits them; kept on uninstall).
[ -f "$HOME/.config/frame-tweaks/scroll-strips.json" ] || {
    mkdir -p "$HOME/.config/frame-tweaks"
    echo '{"vertical": "right", "horizontal": "top", "thickness": 0.04}' > "$HOME/.config/frame-tweaks/scroll-strips.json"
}
install_dashboard_patch scroll-strips "$REPO_DIR/scroll-strips/patch.js"
