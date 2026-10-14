#!/bin/bash
# It stops in the running dashboard within a few seconds. (vr-dashboard, shared, stays.)
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_dashboard_patch float-grab
