#!/bin/bash
# Mouse cursor fix: make KWin draw the pointer so it's visible in desktop mode.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
mkdir -p "$HOME/.config/environment.d"
cp "$TWEAK_DIR/90-kwin-software-cursor.conf" "$HOME/.config/environment.d/"
say "Installed. Takes effect after a reboot (or the next desktop-mode login)."
