#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNITS="$HOME/.config/systemd/user"
DROPIN=frame-tweaks-vr-memory-guard.conf
# (every app with a limit of its own: its scope prefix's drop-in, app-flatpak-<id>-.scope)
apps=()
for d in "$UNITS"/app-flatpak-*-.scope.d; do
    [ -f "$d/$DROPIN" ] && apps+=("$(basename "$d" .d)")
done
for unit in app.slice "${apps[@]}" steamvr.service frame-tweaks-dictate-engine.service \
        frame-tweaks-dictate-button.service app-ftmirror.slice; do
    remove_files "$UNITS/$unit.d/$DROPIN"
    rmdir "$UNITS/$unit.d" 2>/dev/null || true
done
sysctl_user daemon-reload || true
# (The limits set on running units stay until they stop: lift them now.)
sysctl_user set-property --runtime app.slice MemoryMax=infinity MemorySwapMax=infinity || true
for prefix in "${apps[@]}"; do
    for scope in $(sysctl_user list-units --type=scope --state=running --plain --no-legend "${prefix%.scope}*.scope" 2>/dev/null | awk '{print $1}'); do
        sysctl_user set-property --runtime "$scope" MemoryMax=infinity MemorySwapMax=infinity || true
    done
done
remove_files "$BIN/vr-memory-guard-tool"
say "$(t 'Kept your limits in %s and %s.' "$HOME/.config/frame-tweaks/vr-memory-guard.conf" "$HOME/.config/frame-tweaks/vr-memory-guard-apps.conf")"
