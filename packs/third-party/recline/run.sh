#!/bin/bash
# The Start button. Recline-VR's dashboard panel (recline_overlay) is meant to start with SteamVR
# (its installer registers it), but a panel that quit or crashed stays gone until SteamVR
# restarts, and restarting SteamVR reloads the whole headset session; `reclinectl status` then
# says "overlay: NOT running". Here: start the panel the way SteamVR does (its binary, from the
# install folder, which its manifest's paths are relative to) when SteamVR runs and it doesn't,
# registering it again first if it isn't any more. Said with a notification: a button, no terminal.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ROOT="$HOME/.local/share/recline-vr"
BINDIR="$ROOT/bin/linuxarm64"
CTL="$BINDIR/reclinectl"
OVERLAY="$BINDIR/recline_overlay"
tell() { notify-send -a "Frame Tweaks" "Recline" "$*" 2>/dev/null || true; echo "$*"; }
running() { pgrep -f "^$OVERLAY( |$)" >/dev/null; }
[ -x "$CTL" ] && [ -x "$OVERLAY" ] || { tell "$(t 'Not installed: tick Recline and Apply changes first.')"; exit 1; }
if ! sysctl_user is-active --quiet steamvr.service; then
    tell "$(t 'SteamVR is not running: Recline starts with it.')"
    exit 0
fi
if running; then
    timeout 10 "$CTL" panel show >/dev/null 2>&1 || true
    tell "$(t "Already running: its panel is in the SteamVR dashboard.")"
    exit 0
fi
# (registered: "registered: yes" in its status; otherwise SteamVR wouldn't start it next time either)
timeout 15 "$CTL" status 2>/dev/null | grep -q '^registered:[[:space:]]*yes' ||
    timeout 15 "$CTL" register >/dev/null 2>&1 || true
(cd "$ROOT" && setsid -f "$OVERLAY" >/dev/null 2>&1 </dev/null)
for _ in 1 2 3 4 5 6 7 8 9 10; do
    if running; then
        timeout 10 "$CTL" panel show >/dev/null 2>&1 || true
        tell "$(t 'Started: its panel is in the SteamVR dashboard.')"
        exit 0
    fi
    sleep 1
done
tell "$(t "Could not start Recline's panel: %s says why." "$CTL status")"
exit 1
