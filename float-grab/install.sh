#!/bin/bash
# Float in World also picks the window up for placing (vr-dashboard).
source "$(dirname "$0")/../lib/common.sh"
install_dashboard_patch float-grab "$REPO_DIR/float-grab/patch.js"
