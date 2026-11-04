#!/bin/bash
# The Turn off / Turn on button (its label: run-label.sh): the patch stays installed and ticked,
# only told to do nothing, within a few seconds in the running dashboard (no SteamVR restart).
# Unticking still removes it. (lib/common.sh dashboard_patch_switch: how the setting gets there.)
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
dashboard_patch_toggle float-grab "$(t 'Pick up when floating')" \
    "$(t 'Turned on: Float in World picks the window up for placing.')" \
    "$(t 'Turned off: Float in World only floats the window, as in SteamVR.')"
