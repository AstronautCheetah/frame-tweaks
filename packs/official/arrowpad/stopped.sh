#!/bin/bash
# Run by ./install.sh after it stopped the pad: a stopped pad can't release keys it held down,
# so make sure no modifier stays pressed.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/ydotool" ] && clear_stuck_modifiers
exit 0
