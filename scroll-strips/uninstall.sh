#!/bin/bash
# Scroll strips disappear from the dashboard within a few seconds. (vr-dashboard, shared, stays.)
source "$(dirname "$0")/../lib/common.sh"
remove_dashboard_patch scroll-strips
# The desktop's permission to let us scroll it (Remote Desktop portal restore token).
remove_files "$HOME/.local/state/frame-tweaks/remote-desktop.token"
