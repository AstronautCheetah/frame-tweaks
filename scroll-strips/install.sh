#!/bin/bash
# Big scroll strips beside floating windows (vr-dashboard; scrolls with XTest wheel clicks).
source "$(dirname "$0")/../lib/common.sh"
# Settings (the installer window edits them; kept on uninstall).
[ -f "$HOME/.config/frame-tweaks/scroll-strips.json" ] || {
    mkdir -p "$HOME/.config/frame-tweaks"
    echo '{"vertical": "right", "horizontal": "top", "thickness": 0.04}' > "$HOME/.config/frame-tweaks/scroll-strips.json"
}
install_dashboard_patch scroll-strips "$REPO_DIR/scroll-strips/patch.js"
