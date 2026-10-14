#!/bin/bash
# Grab guard: a notification when desktop mode has taken all input (Right Ctrl), and a log of
# which device sent it.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
install -m755 "$TWEAK_DIR/grab-guard" "$BIN/"
mkdir -p "$HOME/.config/systemd/user" "$HOME/.local/state/frame-tweaks/logs"
cp "$TWEAK_DIR/grab-guard.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable --now grab-guard
sysctl_user restart grab-guard
say "Watching. If desktop mode takes all input, a notification says so (tap Right Ctrl to release)."
