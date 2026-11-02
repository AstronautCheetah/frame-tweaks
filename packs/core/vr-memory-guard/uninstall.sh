#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNITS="$HOME/.config/systemd/user"
DROPIN=frame-tweaks-vr-memory-guard.conf
for unit in app.slice app-flatpak-org.mozilla.firefox-.scope steamvr.service; do
    remove_files "$UNITS/$unit.d/$DROPIN"
    rmdir "$UNITS/$unit.d" 2>/dev/null || true
done
sysctl_user daemon-reload || true
# (The limits set on running units stay until they stop: lift them now.)
sysctl_user set-property --runtime app.slice MemoryMax=infinity MemorySwapMax=infinity || true
for scope in $(sysctl_user list-units --type=scope --state=running --plain --no-legend 'app-flatpak-org.mozilla.firefox-*.scope' 2>/dev/null | awk '{print $1}'); do
    sysctl_user set-property --runtime "$scope" MemoryMax=infinity MemorySwapMax=infinity || true
done
say "$(t 'Kept your limits in %s.' "$HOME/.config/frame-tweaks/vr-memory-guard.conf")"
