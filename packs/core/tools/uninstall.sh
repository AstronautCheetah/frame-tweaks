#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# (the watch itself was stopped first: processes: in README.md)
remove_files "$BIN/restart-plasmashell" "$BIN/taskbar-guard" "$HOME/.config/autostart/frame-tweaks-taskbar-guard.desktop"
