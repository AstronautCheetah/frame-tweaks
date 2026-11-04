#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
sysctl_user disable --now frame-tweaks-tray-host.service 2>/dev/null || true
remove_files "$BIN/frame-tweaks-tray-host" "$HOME/.config/systemd/user/frame-tweaks-tray-host.service"
sysctl_user daemon-reload || true
