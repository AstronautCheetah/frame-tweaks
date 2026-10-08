#!/bin/bash
# label: Restart
source "$(dirname "$0")/../lib/common.sh"
sysctl_user restart ydotoold && notify-send -a ydotool "ydotoold restarted"
