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

mkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"
install -m644 "$DIR/icons/frame-tweaks.png" "$HOME/.local/share/icons/hicolor/256x256/apps/frame-tweaks.png"
touch "$HOME/.local/share/icons/hicolor"
cat > "$HOME/.local/share/applications/steam-frame-tweaks.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Steam Frame Tweaks
Comment=Install, check and remove Steam Frame desktop-mode tweaks
Exec=env FRAME_TWEAKS_GUI=1 $DIR/install.sh gui
Icon=frame-tweaks
Terminal=false
Categories=Settings;Utility;
DESKTOP
update-desktop-database -q "$HOME/.local/share/applications" 2>/dev/null || true
touch "$HOME/.local/share/applications"    # Steam's "+" menu rescans on this

echo "Installed 'Steam Frame Tweaks' in the app menu."
if [ -n "${WAYLAND_DISPLAY:-${DISPLAY:-}}" ] && command -v kdialog >/dev/null; then
    exec "$DIR/install.sh" gui
else
    exec "$DIR/install.sh"
fi
