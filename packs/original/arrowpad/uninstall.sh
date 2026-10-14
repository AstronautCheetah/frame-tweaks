#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
"$BIN/arrowpad" --quit --desktop 2>/dev/null || true
"$BIN/arrowpad" --quit --vr 2>/dev/null || true
# Anything still running (an older version that didn't answer): stop it, so a reinstall really
# starts the new one. Quitting releases held keys; a forced stop can't, so release them too.
if pgrep -f "^$HOME/.local/share/arrowpad/venv/bin/python $HOME/.local/share/arrowpad/arrowpad.py" >/dev/null; then
    pkill -f "^$HOME/.local/share/arrowpad/venv/bin/python $HOME/.local/share/arrowpad/arrowpad.py" || true
    sleep 1
    clear_stuck_modifiers
    say "$(t 'stopped a running Arrow Pad')"
fi
remove_files "$ICONS/256x256/apps/frame-tweaks-arrowpad.png" "$BIN/arrowpad" "$APPS/arrowpad.desktop" "$APPS/arrowpad-vr.desktop" "$HOME/.local/share/arrowpad/arrowpad.py" "$HOME/.local/share/arrowpad/vroverlay.py" "$HOME/.local/share/arrowpad/haptics.py" "$HOME/.local/share/arrowpad/vr" "$HOME/.local/share/arrowpad/__pycache__"
# The PyQt6 venv is shared with the NordVPN tray, Screen snip and the installer window.
remove_qt_venv
