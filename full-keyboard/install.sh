#!/bin/bash
# Full Keyboard (TaiKeid): full-size VR keyboard for the dashboard + local apps.
source "$(dirname "$0")/../lib/common.sh"
REL=https://github.com/TaiKeid/steam-frame-full-keyboard/releases/latest/download
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
curl -fsSL -o "$T/SHA256SUMS" "$REL/SHA256SUMS"
ARCHIVE=$(grep -m1 -oE 'framekeyboard-[0-9.]+-aarch64\.tar\.gz' "$T/SHA256SUMS")
VER=$(echo "$ARCHIVE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ -e "$HOME/.local/share/framekeyboard/releases/$VER" ]; then
    say "Full Keyboard $VER already installed"; exit 0
fi
pgrep -x framekeyboard >/dev/null && die "Full Keyboard is running: close it from its toolbar first"
say "Downloading Full Keyboard $VER"
curl -fL# -o "$T/$ARCHIVE" "$REL/$ARCHIVE"
(cd "$T" && sha256sum -c --ignore-missing --quiet SHA256SUMS) || die "checksum mismatch"
tar -xzf "$T/$ARCHIVE" -C "$T"
bash "$T/${ARCHIVE%.tar.gz}/install.sh"
say "Open 'Full Keyboard' from the VR dashboard's app launcher (VR session must be running)."
