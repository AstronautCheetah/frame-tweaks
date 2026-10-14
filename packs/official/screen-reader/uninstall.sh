#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
restore_kconfig screen-reader
[ "$(kreadconfig6 --file kaccessrc --group ScreenReader --key Enabled 2>/dev/null)" = true ] ||
    say "Screen reader off from the next desktop-mode start (Meta+Alt+S turns it off now)."
