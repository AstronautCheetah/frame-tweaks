#!/bin/bash
# SteamVR internals the curvature patch relies on.
D="$HOME/.local/share/frame-tweaks/curvature/sft-curvature"
[ -x "$D" ] || D="$(dirname "$0")/sft-curvature"
r=$("$D" check) || { echo "SteamVR dashboard code changed ($r): the patch stays off"; exit 1; }
[ -f "$HOME/.config/openvr/config/steamvr.vrsettings" ] || { echo "steamvr.vrsettings not found"; exit 1; }
echo "SteamVR dashboard code as expected"
