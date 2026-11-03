#!/bin/bash
# The Run button's label, following the panel's state (the window asks with each status check,
# and again a few seconds after Run): Hide while the panel is shown, Show otherwise. Shown means
# its service runs and config.json says "visible": true: the program run a second time flips that
# in the file, and the running one reads it back. That's how its menu entry shows and hides it,
# and what run.sh does. (Written by the program with the key and a space: `"visible": true`.)
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNIT=frame-perf-overlay.service
CONF="${XDG_CONFIG_HOME:-$HOME/.config}/frame-perf-overlay/config.json"
if sysctl_user is-active --quiet "$UNIT" && grep -q '"visible": true' "$CONF" 2>/dev/null; then
    t 'Hide'
else
    t 'Show'
fi
echo
