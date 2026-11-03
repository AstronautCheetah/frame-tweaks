#!/bin/bash
# The Open button. The app is meant to start with SteamVR (its user service is wanted by
# steamvr.service), but its installer's `systemctl --user enable` fails quietly in a desktop-mode
# terminal, where Frame Tweaks runs it (no user bus there: lib/common.sh sysctl_user). Here:
# enable the service if it isn't, start it when SteamVR runs and it doesn't, and open its panel
# in the dashboard (the program run with --open, its menu entry's command). Said with a
# notification: a button, no terminal.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNIT=framepip.service
PROG="$HOME/.local/share/framepip/bin/framepip"
tell() { notify-send -a "Frame Tweaks" "$(t 'Passthrough PiP')" "$*" 2>/dev/null || true; echo "$*"; }
[ -x "$PROG" ] || { tell "$(t 'Not installed: tick Passthrough PiP and Apply changes first.')"; exit 1; }
fixed=""
if [ -f "$HOME/.config/systemd/user/$UNIT" ] && [ "$(sysctl_user is-enabled "$UNIT" 2>/dev/null)" != enabled ]; then
    if sysctl_user enable "$UNIT" >/dev/null 2>&1; then
        fixed=" $(t 'From now on it starts with SteamVR, as its installer meant to set up.')"
    else
        fixed=" $(t 'It is not set to start with SteamVR, and that could not be fixed: run %s in a terminal.' \
                   "systemctl --user enable $UNIT")"
    fi
fi
if ! sysctl_user is-active --quiet steamvr.service; then
    tell "$(t 'SteamVR is not running: the camera view shows once it is.')$fixed"
elif sysctl_user is-active --quiet "$UNIT" || sysctl_user start "$UNIT" 2>/dev/null; then
    setsid -f "$PROG" --open >/dev/null 2>&1 </dev/null
    tell "$(t 'Opened: its panel is in the SteamVR dashboard; double-tap View on the left controller shows or hides the camera view.')$fixed"
else
    tell "$(t 'Could not start %s: see %s' "$UNIT" "journalctl --user -u $UNIT")$fixed"
    exit 1
fi
