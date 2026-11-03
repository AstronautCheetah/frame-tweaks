#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# The VR overlay when this was started from VR (display :0), else the desktop pad.
if [ "${DISPLAY:-}" = ":0" ]; then where=vr; else where=desktop; fi
# As a unit of its own (lib/common.sh run_unit: ft-arrowpad-desktop or ft-arrowpad-vr), so an
# uninstall stops it whole and memory it leaks can't take VR's. Safe outside this window's
# environment: --desktop reads desktop mode's DISPLAY and XAUTHORITY from its session manager
# (arrowpad.py pick_display), --vr sets DISPLAY=:0 and draws off-screen into a SteamVR overlay, and
# ydotoold's socket is a fixed path in /run/user/<uid>. Already running: the pad run again tells
# that one to hide or show (its single-instance socket), as the menu entry does.
run_unit arrowpad "$where" --memory 600M -- "$BIN/arrowpad" "--$where" || {
    rc=$?
    [ "$rc" -eq 3 ] && exec "$BIN/arrowpad" "--$where"
    exit "$rc"
}
