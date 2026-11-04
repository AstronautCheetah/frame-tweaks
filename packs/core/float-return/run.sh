#!/bin/bash
# The Turn off / Turn on button (its label: run-label.sh): the patch stays installed and ticked,
# only told to do nothing, within a few seconds in the running dashboard (no SteamVR restart).
# Unticking still removes it. (lib/common.sh dashboard_patch_switch: how the setting gets there.)
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
dashboard_patch_toggle float-return "$(t 'Back to the previous window')" \
    "$(t 'Turned on: after you float a window out, the dashboard goes back to the one before.')" \
    "$(t 'Turned off: the dashboard stays as SteamVR leaves it after you float a window out or close one.')"
