#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_dashboard_patch snip-float
remove_files "$BIN/frame-snip" "$APPS/frame-snip.desktop" "$ICONS/256x256/apps/frame-tweaks-snip.png"
say "Kept Tesseract (brew uninstall tesseract) and your snips in ~/Pictures/Screenshots."
