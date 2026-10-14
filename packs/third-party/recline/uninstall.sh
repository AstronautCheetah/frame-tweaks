#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
DEST="$HOME/.local/share/recline-vr"
VRPATHREG=/opt/steamvr/bin/linuxarm64/vrpathreg
if pgrep -x vrserver >/dev/null; then
    [ -e /dev/shm/recline_v1 ] && [ -x "$DEST/reclinectl" ] && timeout 10 "$DEST/reclinectl" reset >/dev/null 2>&1
    [ -x "$DEST/recline_overlay" ] && timeout 20 "$DEST/recline_overlay" --unregister >/dev/null 2>&1 ||
        warn "$(t "couldn't unregister Recline's panel from SteamVR; it will report it missing")"
    pkill -u "$(id -u)" -f "^$DEST/recline_overlay" 2>/dev/null || true
else
    warn "$(t "SteamVR isn't running, so Recline's panel couldn't be unregistered (SteamVR may still list it)")"
fi
[ -x "$VRPATHREG" ] && "$VRPATHREG" removedriver "$DEST/recline" >/dev/null 2>&1
remove_files "$DEST" "$HOME/.cache/frame-tweaks/recline-build"
[ -d "$HOME/.config/recline-vr" ] && say "$(t "Kept Recline's panel options: ~/.config/recline-vr")"
say "$(t 'Restart SteamVR to unload its driver (reboot, or: %s).' "steamvr restart")"
