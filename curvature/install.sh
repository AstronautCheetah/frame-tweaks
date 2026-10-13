#!/bin/bash
# Windows floated into the world start curved: a small SteamVR dashboard patch (vr-dashboard).
source "$(dirname "$0")/../lib/common.sh"
install_dashboard_patch curvature "$REPO_DIR/curvature/patch.js"
