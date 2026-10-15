#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/restart-plasmashell" ] && status_ok "$(t '%s installed' restart-plasmashell)" || status_missing "$(t 'not installed')"
