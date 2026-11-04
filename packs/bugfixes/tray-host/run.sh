#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# (a failed unit's record cleared first, so Restart works whatever happened to it before)
sysctl_user reset-failed frame-tweaks-tray-host.service 2>/dev/null || true
sysctl_user restart frame-tweaks-tray-host.service && notify-send -a "Frame Tweaks" "$(t '%s restarted' frame-tweaks-tray-host)"
