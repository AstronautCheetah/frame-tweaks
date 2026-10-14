#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
DEST="$HOME/.local/share/recline-vr"
[ -x "$DEST/recline_overlay" ] || status_missing "$(t 'not installed')"
v=$(cat "$DEST/.frame-tweaks-version" 2>/dev/null)
grep -qF "$DEST/recline" "$HOME/.config/openvr/openvrpaths.vrpath" 2>/dev/null ||
    status_warn "$(t "Recline %s installed but its driver isn't registered (Reinstall fixes it)" "$v")"
pgrep -x vrserver >/dev/null || status_ok "$(t "Recline %s installed (SteamVR isn't running)" "$v")"
# (Only once the driver made its shared memory: reclinectl would create it otherwise.)
[ -e /dev/shm/recline_v1 ] && timeout 5 "$DEST/reclinectl" status >/dev/null 2>&1 ||
    status_warn "$(t "Recline %s installed; restart SteamVR to load it (or check SteamVR's safe mode)" "$v")"
status_ok "$(t 'Recline %s loaded' "$v")"
