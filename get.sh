#!/bin/bash
# Bootstrap: clone (or update) steam-frame-tweaks into ~/steam-frame-tweaks, add a
# "Steam Frame Tweaks" entry to the app menu, and open the installer.
#   curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/steam-frame-tweaks/main/get.sh | bash
set -euo pipefail
REPO=${FRAME_TWEAKS_REPO:-https://github.com/AstronautCheetah/steam-frame-tweaks.git}
DIR=${FRAME_TWEAKS_DIR:-$HOME/steam-frame-tweaks}

if [ -d "$DIR/.git" ]; then
    echo "Updating $DIR"; git -C "$DIR" pull --ff-only
else
    echo "Cloning into $DIR"; git clone --depth 1 "$REPO" "$DIR"
fi

"$DIR/install.sh" menu

if [ -n "${WAYLAND_DISPLAY:-${DISPLAY:-}}" ] && command -v kdialog >/dev/null; then
    exec "$DIR/install.sh" gui
else
    exec "$DIR/install.sh"
fi
