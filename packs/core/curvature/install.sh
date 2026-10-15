#!/bin/bash
# Windows floated into the world start curved: a small SteamVR dashboard patch (vr-dashboard).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
install_dashboard_patch curvature "$TWEAK_DIR/patch.js"
