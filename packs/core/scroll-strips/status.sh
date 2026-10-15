#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
dashboard_patch_status scroll-strips "$(t 'scroll strips beside floating windows')"
