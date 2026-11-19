#!/bin/bash
# Sleep when idle in VR: a user service that puts the Frame to sleep once the headset has been in
# standby a while (docs/research/idle-sleep.md). Settings: ~/.config/frame-tweaks/auto-sleep.conf.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
install -m755 "$TWEAK_DIR/frame-tweaks-auto-sleep" "$BIN/"
mkdir -p "$HOME/.config/systemd/user"
cp "$TWEAK_DIR/frame-tweaks-auto-sleep.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable frame-tweaks-auto-sleep.service
# (a failed unit's record cleared, so a reinstall starts it again whatever happened to it before)
sysctl_user reset-failed frame-tweaks-auto-sleep.service 2>/dev/null || true
sysctl_user restart frame-tweaks-auto-sleep.service
say "$(t 'The Frame now sleeps once the headset has been in standby a while: %s' "$("$BIN/frame-tweaks-auto-sleep" --status)")"
