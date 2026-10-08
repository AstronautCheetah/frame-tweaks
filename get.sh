#!/bin/bash
# Bootstrap: install (or update) Frame Tweaks into ~/frame-tweaks, add a
# "Frame Tweaks" entry to the app menu, and open the installer.
#   curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/frame-tweaks/main/get.sh | bash
set -euo pipefail
REPO=${FRAME_TWEAKS_REPO:-https://github.com/AstronautCheetah/frame-tweaks.git}
DIR=${FRAME_TWEAKS_DIR:-$HOME/frame-tweaks}
[ -z "${FRAME_TWEAKS_DIR:-}" ] && [ -d "$HOME/steam-frame-tweaks/.git" ] && DIR=$HOME/steam-frame-tweaks   # its old name

# Install the newest release (a vX.Y.Z tag), not whatever is on main right now.
TAG=$(git ls-remote --tags --refs "$REPO" 'v*' | sed 's|.*refs/tags/||' | sort -V | tail -1)
[ -n "$TAG" ] || { echo "Couldn't find a release of $REPO" >&2; exit 1; }
if [ -d "$DIR/.git" ]; then
    echo "Updating $DIR to $TAG"
    git -C "$DIR" fetch --quiet --tags origin && git -C "$DIR" -c advice.detachedHead=false checkout --quiet "$TAG"
else
    echo "Installing $TAG into $DIR"
    git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$TAG" "$REPO" "$DIR"
fi

"$DIR/install.sh" menu

if [ -n "${WAYLAND_DISPLAY:-${DISPLAY:-}}" ] && command -v kdialog >/dev/null; then
    exec "$DIR/install.sh" gui
else
    exec "$DIR/install.sh"
fi
