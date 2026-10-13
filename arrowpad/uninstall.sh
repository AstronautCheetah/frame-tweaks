#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
"$BIN/arrowpad" --quit --desktop 2>/dev/null || true
"$BIN/arrowpad" --quit --vr 2>/dev/null || true
# Anything still running (an older version that didn't answer): stop it, so a reinstall really
# starts the new one. Quitting releases held keys; a forced stop can't, so release them too.
if pgrep -f "^$HOME/.local/share/arrowpad/venv/bin/python $HOME/.local/share/arrowpad/arrowpad.py" >/dev/null; then
    pkill -f "^$HOME/.local/share/arrowpad/venv/bin/python $HOME/.local/share/arrowpad/arrowpad.py" || true
    sleep 1
    YDOTOOL_SOCKET="/run/user/$(id -u)/.ydotool_socket" "$BIN/ydotool" key 125:0 29:0 56:0 42:0 2>/dev/null || true
    say "stopped a running Arrow Pad"
fi
remove_files "$ICONS/256x256/apps/frame-tweaks-arrowpad.png" "$BIN/arrowpad" "$APPS/arrowpad.desktop" "$APPS/arrowpad-vr.desktop" "$HOME/.config/arrowpad-vr.json" "$HOME/.local/share/arrowpad/arrowpad.py" "$HOME/.config/arrowpad.json"
[ -x "$BIN/nordvpn-tray" ] || remove_files "$QT_VENV"
