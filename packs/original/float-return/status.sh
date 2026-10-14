#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
dashboard_patch_status float-return "$(t 'back to the previous window after floating one')"
