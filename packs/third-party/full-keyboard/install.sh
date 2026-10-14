#!/bin/bash
# Full Keyboard (TaiKeid): full-size VR keyboard for the dashboard + local apps.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
VER=$(pin_version full-keyboard)
ARCHIVE="framekeyboard-$VER-aarch64.tar.gz"
if [ -e "$HOME/.local/share/framekeyboard/releases/$VER" ]; then
    say "$(t 'Full Keyboard %s already installed' "$VER")"; exit 0
fi
pgrep -x framekeyboard >/dev/null && die "$(t 'Full Keyboard is running: close it from its toolbar first')"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
say "$(t 'Downloading Full Keyboard %s' "$VER")"
fetch_pinned full-keyboard "$T/$ARCHIVE"
tar -xzf "$T/$ARCHIVE" -C "$T"
bash "$T/${ARCHIVE%.tar.gz}/install.sh"
say "$(t "Open 'Full Keyboard' from the VR dashboard's app launcher (VR session must be running).")"
