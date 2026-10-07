#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
pgrep -x framekeyboard >/dev/null && die "Full Keyboard is running: close it first"
remove_files "$BIN/framekeyboard" "$APPS/framekeyboard.desktop" "$HOME/.local/share/framekeyboard"
say "Kept its settings in ~/.config/framekeyboard."
