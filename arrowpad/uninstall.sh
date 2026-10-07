#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
"$BIN/arrowpad" --quit 2>/dev/null || true
remove_files "$BIN/arrowpad" "$APPS/arrowpad.desktop" "$HOME/.local/share/arrowpad/arrowpad.py" "$HOME/.config/arrowpad.json"
[ -x "$BIN/nordvpn-tray" ] || remove_files "$QT_VENV"
