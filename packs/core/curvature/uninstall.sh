#!/bin/bash
# Windows you already floated keep their current curvature. (vr-dashboard, shared, stays.)
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_dashboard_patch curvature
