#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
sysctl_user disable --now grab-guard 2>/dev/null || true
remove_files "$BIN/grab-guard" "$HOME/.config/systemd/user/grab-guard.service"
sysctl_user daemon-reload
say "Kept its log (~/.local/state/frame-tweaks/logs/grab-guard.log)."
