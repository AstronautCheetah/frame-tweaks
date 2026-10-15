#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
sysctl_user disable --now ydotoold 2>/dev/null || true
remove_files "$BIN/ydotool" "$BIN/ydotoold" "$HOME/.config/systemd/user/ydotoold.service"
sysctl_user daemon-reload || true
