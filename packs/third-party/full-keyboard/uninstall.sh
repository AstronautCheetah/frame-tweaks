#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
pgrep -x framekeyboard >/dev/null && die "$(t 'Full Keyboard is running: close it first')"
remove_desktop framekeyboard.desktop
remove_files "$BIN/framekeyboard" "$HOME/.local/share/framekeyboard"
