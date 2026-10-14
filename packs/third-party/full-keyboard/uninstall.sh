#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
pgrep -x framekeyboard >/dev/null && die "$(t 'Full Keyboard is running: close it first')"
remove_files "$BIN/framekeyboard" "$APPS/framekeyboard.desktop" "$HOME/.local/share/framekeyboard"
say "$(t 'Kept its settings in ~/.config/framekeyboard.')"
