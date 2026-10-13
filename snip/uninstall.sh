#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
remove_files "$BIN/frame-snip" "$HOME/.local/share/frame-tweaks/snip" "$APPS/frame-snip.desktop" "$ICONS/256x256/apps/frame-tweaks-snip.png"
say "Kept Tesseract (brew uninstall tesseract) and your snips in ~/Pictures/Screenshots."
