#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
src=$(pgrep -u "$(id -u)" -x ksmserver | head -1) || true
[ -n "$src" ] || { notify-send -a "$(t 'Shared clipboard')" "$(t "Desktop mode isn't running")" "$(t '%s starts with it.' clipboard-sync)"; exit 1; }
mapfile -d "" envs < "/proc/$src/environ"
(cd "$HOME" && env -i "${envs[@]}" setsid -f "$BIN/clipboard-sync-start" >/dev/null 2>&1 </dev/null)
notify-send -a "$(t 'Shared clipboard')" "$(t '%s restarted' clipboard-sync)" "$(t 'Copy in VR, paste in the desktop, and back.')"
