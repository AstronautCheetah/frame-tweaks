#!/bin/bash
# After you float the window the dashboard shows, it goes back to the previous one (vr-dashboard).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
install_dashboard_patch float-return "$TWEAK_DIR/patch.js"
