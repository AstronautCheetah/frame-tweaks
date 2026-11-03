#!/bin/bash
# The Show button. The panel is meant to start with SteamVR (its user service is wanted by
# steamvr.service), but its installer's `systemctl --user enable` fails quietly in a desktop-mode
# terminal, where Frame Tweaks runs it (no user bus there: lib/common.sh sysctl_user), so the
# panel sat installed and never started. Here: enable the service if it isn't, start it when
# SteamVR runs and it doesn't, and when it runs already, run the program once, which shows or
# hides the panel (its menu entry's words). Said with a notification: a button, no terminal.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNIT=frame-perf-overlay.service
tell() { notify-send -a "Frame Tweaks" "$(t 'Performance Overlay')" "$*" 2>/dev/null || true; echo "$*"; }
[ -x "$HOME/.local/bin/frame-perf-overlay" ] ||
    { tell "$(t 'Not installed: tick Performance Overlay and Apply changes first.')"; exit 1; }
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
    tell "$(t 'SteamVR is not running: the panel shows once it is.')$fixed"
elif [ ! -f "$HOME/.config/systemd/user/$UNIT" ]; then
    # (a version without the service: the program itself, as its menu entry runs it)
    setsid -f gtk-launch frame-perf-overlay >/dev/null 2>&1 </dev/null
    tell "$(t 'Started: look for the panel in VR; its Perf tab in the SteamVR dashboard has the settings.')"
elif sysctl_user is-active --quiet "$UNIT"; then
    # (running: the program run again shows or hides the panel, its menu entry says)
    setsid -f gtk-launch frame-perf-overlay >/dev/null 2>&1 </dev/null
    tell "$(t 'Shown or hidden in VR (it was running).')$fixed"
elif sysctl_user start "$UNIT" 2>/dev/null; then
    tell "$(t 'Started: look for the panel in VR; its Perf tab in the SteamVR dashboard has the settings.')$fixed"
else
    tell "$(t 'Could not start %s: see %s' "$UNIT" "journalctl --user -u $UNIT")$fixed"
    exit 1
fi
