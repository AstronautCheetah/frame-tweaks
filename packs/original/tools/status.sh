#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/restart-plasmashell" ] && status_ok "restart-plasmashell installed" || status_missing "not installed"
