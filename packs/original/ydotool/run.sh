#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
sysctl_user restart ydotoold && notify-send -a ydotool "ydotoold restarted"
