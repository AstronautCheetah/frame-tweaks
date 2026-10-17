#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
"$BIN/arrowpad" --quit --desktop 2>/dev/null || true
"$BIN/arrowpad" --quit --vr 2>/dev/null || true
# A pad asked to quit closes on its own, letting go of its keys and of SteamVR: give it 2 s (it was
# stopped at once, in the middle of that).
pad="^$HOME/.local/share/arrowpad/venv/bin/python $HOME/.local/share/arrowpad/arrowpad.py"
for _ in $(seq 20); do pgrep -f "$pad" >/dev/null || break; sleep 0.1; done
# Anything still running (an older version that didn't answer): stop it, so a reinstall really
# starts the new one. Quitting releases held keys; a forced stop can't, so release them too.
if pgrep -f "$pad" >/dev/null; then
    pkill -f "$pad" || true
    sleep 1
    clear_stuck_modifiers
    say "$(t 'stopped a running Arrow Pad')"
fi
remove_dashboard_patch arrowpad-keyboard
remove_icon frame-tweaks-arrowpad
remove_desktop arrowpad.desktop arrowpad-vr.desktop
remove_files "$BIN/arrowpad" "$HOME/.local/share/arrowpad/arrowpad.py" "$HOME/.local/share/arrowpad/vroverlay.py" "$HOME/.local/share/arrowpad/haptics.py" "$HOME/.local/share/arrowpad/vr" "$HOME/.local/share/arrowpad/__pycache__"
# The PyQt6 venv is shared with the NordVPN tray, Screen snip and the installer window.
remove_qt_venv
