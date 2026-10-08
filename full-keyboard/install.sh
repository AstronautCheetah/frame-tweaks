#!/bin/bash
# Full Keyboard (TaiKeid): full-size VR keyboard for the dashboard + local apps.
source "$(dirname "$0")/../lib/common.sh"
VER=$(pin_version full-keyboard)
ARCHIVE="framekeyboard-$VER-aarch64.tar.gz"
if [ -e "$HOME/.local/share/framekeyboard/releases/$VER" ]; then
    say "Full Keyboard $VER already installed"; exit 0
fi
pgrep -x framekeyboard >/dev/null && die "Full Keyboard is running: close it from its toolbar first"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
say "Downloading Full Keyboard $VER"
fetch_pinned full-keyboard "$T/$ARCHIVE"
tar -xzf "$T/$ARCHIVE" -C "$T"
bash "$T/${ARCHIVE%.tar.gz}/install.sh"
say "Open 'Full Keyboard' from the VR dashboard's app launcher (VR session must be running)."
