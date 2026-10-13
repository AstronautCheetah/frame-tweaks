#!/bin/bash
# SteamVR internals the dashboard patches rely on.
D="$HOME/.local/share/frame-tweaks/vr-dashboard/sft-dashboard"
[ -x "$D" ] || D="$(dirname "$0")/sft-dashboard"
r=$("$D" check) || { echo "SteamVR dashboard code changed ($r): those patches stay off"; exit 1; }
[ -f "$HOME/.config/openvr/config/steamvr.vrsettings" ] || { echo "steamvr.vrsettings not found"; exit 1; }
echo "SteamVR dashboard code as expected"
