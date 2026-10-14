#!/bin/bash
# Float in World also picks the window up for placing (vr-dashboard).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
install_dashboard_patch float-grab "$TWEAK_DIR/patch.js"
