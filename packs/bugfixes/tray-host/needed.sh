#!/bin/bash
# Needed where the VR session gives apps KDE's Qt platform theme (SteamOS 0.5.7's beta on:
# /usr/lib/steamos/gamescope-session, "export QT_QPA_PLATFORMTHEME=kde"): only then do Qt 5 tray
# icons go through D-Bus, find no tray and retry until the session's bus runs out
# (docs/research/tray-icon-flood.md). Checked in the file that sets it, not by SteamOS version:
# the beta and stable branches number theirs differently. (FRAME_TWEAKS_GAMESCOPE_SESSION: another
# file, for the tests.)
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
f=${FRAME_TWEAKS_GAMESCOPE_SESSION:-/usr/lib/steamos/gamescope-session}
if grep -qsE '^[[:space:]]*(export[[:space:]]+)?QT_QPA_PLATFORMTHEME=["'"'"']?kde' "$f"; then
    exit 0
fi
echo "$(t "this SteamOS's VR session doesn't give apps KDE's Qt theme, so tray icons can't flood its D-Bus")"
exit 1
