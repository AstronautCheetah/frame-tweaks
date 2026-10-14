#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_dashboard_patch snip-float
remove_files "$BIN/frame-snip" "$APPS/frame-snip.desktop" "$ICONS/256x256/apps/frame-tweaks-snip.png"
# The PyQt6 venv is shared with Arrow Pad and the NordVPN tray: only the last one removes it.
[ -x "$BIN/arrowpad" ] || [ -x "$BIN/nordvpn-tray" ] || remove_files "$QT_VENV"
say "Kept Tesseract and wl-clipboard (brew uninstall tesseract wl-clipboard) and your snips in ~/Pictures/Screenshots."
