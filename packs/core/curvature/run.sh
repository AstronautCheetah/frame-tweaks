#!/bin/bash
# The Turn off / Turn on button (its label: run-label.sh): the patch stays installed and ticked,
# only told to do nothing, within a few seconds in the running dashboard (no SteamVR restart).
# Unticking still removes it. (lib/common.sh dashboard_patch_switch: how the setting gets there.)
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
dashboard_patch_toggle curvature "$(t 'Curved world windows')" \
    "$(t 'Turned on: windows you float into the world start curved.')" \
    "$(t 'Turned off: windows you float into the world start flat, as in SteamVR. Windows curved already stay as they are.')"
