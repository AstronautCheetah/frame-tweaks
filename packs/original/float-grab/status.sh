#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
dashboard_patch_status float-grab "$(t 'Float in World picks the window up')"
