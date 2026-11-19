#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
sysctl_user disable --now frame-tweaks-auto-sleep.service 2>/dev/null || true
remove_files "$BIN/frame-tweaks-auto-sleep" "$HOME/.config/systemd/user/frame-tweaks-auto-sleep.service"
sysctl_user daemon-reload || true
