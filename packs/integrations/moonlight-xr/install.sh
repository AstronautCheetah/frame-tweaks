#!/bin/bash
# Moonlight XR for Frame: its pinned release, checked, installed by its own installer (program in
# ~/Games/MoonlightXRNative, Steam library entry, SteamVR's per-app settings, dock icon), then
# Frame Tweaks' part: an app-menu entry you can see (the installer's own is hidden: it's there for
# the SteamVR dock icon to match) and the uninstall's helper kept.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
HOME_DIR="$HOME/Games/MoonlightXRNative"
VER=$(pin_version moonlight-xr)
# (its installer adds the library entry through the running Steam; without it, it says so and skips it)
pgrep -u "$(id -u)" -x steam >/dev/null ||
    warn "$(t "Steam isn't running: the program installs, but its Steam library entry is added only when you install it again with Steam running")"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
say "$(t 'Downloading %s %s' "Moonlight XR for Frame" "$VER")"
fetch_pinned moonlight-xr "$T/mlxr.tar.gz"
tar -xzf "$T/mlxr.tar.gz" -C "$T"
(cd "$T/MoonlightXRNative" && ./install.sh) || die "$(t "Moonlight XR's installer stopped (its log: %s)" "$HOME_DIR/install.log")"
# Its README removes the dock icon with dock_icon.py from the unpacked release, which is gone by
# then: kept beside the program for uninstall.sh.
install -m644 "$T/MoonlightXRNative/dock_icon.py" "$HOME_DIR/.frame-tweaks-dock_icon.py"
install_desktop "$TWEAK_DIR/moonlight-xr.desktop"
say "$(t 'Start it from your Steam library, the app menu, or Open on its row; pair with your PC on first start.')"
