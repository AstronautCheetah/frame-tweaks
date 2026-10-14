#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_files "$BIN/capped" "$HOME/.config/systemd/user/app-flatpak-com.vscodium.codium-.scope.d/memcap.conf"
rmdir "$HOME/.config/systemd/user/app-flatpak-com.vscodium.codium-.scope.d" 2>/dev/null || true
sysctl_user daemon-reload || true
say "Kept your limits in ~/.config/frame-tweaks/memcap.conf."
