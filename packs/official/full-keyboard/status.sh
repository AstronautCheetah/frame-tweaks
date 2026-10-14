#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
cur="$HOME/.local/share/framekeyboard/current"
[ -L "$cur" ] || status_missing "Full Keyboard not installed"
status_ok "Full Keyboard $(basename "$(readlink "$cur")")"
