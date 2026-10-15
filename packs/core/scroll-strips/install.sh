#!/bin/bash
# Big scroll strips beside windows (vr-dashboard). They scroll with arrow and page keys (ydotool),
# in the window you last clicked, the desktop included.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/ydotool" ] || "$(tweak_dir ydotool)/install.sh"
# Settings (the installer window edits them; kept on uninstall).
[ -f "$HOME/.config/frame-tweaks/scroll-strips.json" ] || {
    mkdir -p "$HOME/.config/frame-tweaks"
    echo '{"vertical": "right", "horizontal": "top", "thickness": 0.04}' > "$HOME/.config/frame-tweaks/scroll-strips.json"
}
install_dashboard_patch scroll-strips "$TWEAK_DIR/patch.js"
