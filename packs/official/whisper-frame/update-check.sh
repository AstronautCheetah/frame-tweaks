#!/bin/bash
# Prints "<installed> <pinned>" for the installer window's update hint: a newer pinned version
# arrives with a Frame Tweaks update (pins move only after review, see dev/check-pins.sh).
cur=$(cat "$HOME/.local/lib/whisper-frame/VERSION" 2>/dev/null) || exit 1
echo "$cur $(sed -n 's/^version=//p' "$(dirname "$0")/pin")"
