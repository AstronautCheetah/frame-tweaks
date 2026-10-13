#!/bin/bash
# label: Restart
source "$(dirname "$0")/../lib/common.sh"
src=$(pgrep -u "$(id -u)" -x ksmserver | head -1) || true
[ -n "$src" ] || { notify-send -a "Shared clipboard" "Desktop mode isn't running" "clipboard-sync starts with it."; exit 1; }
mapfile -d "" envs < "/proc/$src/environ"
(cd "$HOME" && env -i "${envs[@]}" setsid -f "$BIN/clipboard-sync-start" >/dev/null 2>&1 </dev/null)
notify-send -a "Shared clipboard" "clipboard-sync restarted" "Copy in VR, paste in the desktop, and back."
