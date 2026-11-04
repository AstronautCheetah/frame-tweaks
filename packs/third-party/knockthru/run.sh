#!/bin/bash
# The Start button. KnockThru is meant to start with SteamVR (its installer registers it), but a
# copy that quit or crashed stays gone until SteamVR restarts, and a restart of SteamVR reloads
# the whole headset session. Here: start its resident app (--run, what SteamVR itself starts)
# when SteamVR runs and it doesn't; if it isn't registered with SteamVR any more, its own
# --install registers it again and starts it, as its README's first start does. Said with a
# notification: a button, no terminal.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
PROG="$HOME/KnockThru/knockthru"
tell() { notify-send -a "Frame Tweaks" "KnockThru" "$*" 2>/dev/null || true; echo "$*"; }
[ -x "$PROG" ] || { tell "$(t 'Not installed: tick KnockThru and Apply changes first.')"; exit 1; }
if ! sysctl_user is-active --quiet steamvr.service; then
    tell "$(t 'SteamVR is not running: KnockThru starts with it.')"
    exit 0
fi
if pgrep -f "^$PROG --run( |$)" >/dev/null; then
    tell "$(t 'Already running: knock twice to turn passthrough on or off; its settings are in its tab in the SteamVR dashboard.')"
    exit 0
fi
# (--status says "Registered with SteamVR: yes" once its manifest is in SteamVR's list)
if timeout 15 "$PROG" --status 2>/dev/null | grep -q '^Registered with SteamVR: yes'; then
    setsid -f "$PROG" --run >/dev/null 2>&1 </dev/null
else
    timeout 60 "$PROG" --install >/dev/null 2>&1 </dev/null
fi
for _ in 1 2 3 4 5 6 7 8 9 10; do
    pgrep -f "^$PROG --run( |$)" >/dev/null &&
        { tell "$(t 'Started: knock twice to turn passthrough on or off.')"; exit 0; }
    sleep 1
done
tell "$(t 'Could not start KnockThru: %s writes a report for its author.' "$PROG --report")"
exit 1
