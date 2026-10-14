#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# The VR overlay when this was started from VR (display :0), else the desktop pad.
if [ "${DISPLAY:-}" = ":0" ]; then exec gtk-launch arrowpad-vr; else exec gtk-launch arrowpad; fi
