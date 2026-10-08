#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
"$BIN/arrowpad" --quit --desktop 2>/dev/null || true
"$BIN/arrowpad" --quit --vr 2>/dev/null || true
remove_files "$ICONS/256x256/apps/frame-tweaks-arrowpad.png" "$BIN/arrowpad" "$APPS/arrowpad.desktop" "$APPS/arrowpad-vr.desktop" "$HOME/.config/arrowpad-vr.json" "$HOME/.local/share/arrowpad/arrowpad.py" "$HOME/.config/arrowpad.json"
[ -x "$BIN/nordvpn-tray" ] || remove_files "$QT_VENV"
