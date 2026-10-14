#!/bin/bash
# Prints "<installed> <pinned>" for the installer window's update hint: a newer pinned version
# arrives with a Frame Tweaks update (pins move only after review, see dev/check-pins.sh).
cur=$(basename "$(readlink "$HOME/.local/share/framekeyboard/current" 2>/dev/null)") || exit 1
[ -n "$cur" ] && [ "$cur" != . ] || exit 1
echo "$cur $(sed -n 's/^version=//p' "$(dirname "$0")/pin")"
