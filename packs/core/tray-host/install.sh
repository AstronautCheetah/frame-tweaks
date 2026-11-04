#!/bin/bash
# Tray icon crash fix: a tray watcher on the VR session's D-Bus, so apps with a tray icon stop
# retrying (docs/research/tray-icon-flood.md).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# SteamOS's own Python runs it, for its PyGObject (gi): a SteamOS without it would leave the
# service failing at every start.
/usr/bin/python3 -c 'import gi; gi.require_version("Gio", "2.0"); from gi.repository import Gio' 2>/dev/null ||
    warn "$(t "SteamOS's Python has no PyGObject (gi), which %s needs: it won't start" frame-tweaks-tray-host)"
install -m755 "$TWEAK_DIR/frame-tweaks-tray-host" "$BIN/"
mkdir -p "$HOME/.config/systemd/user"
cp "$TWEAK_DIR/frame-tweaks-tray-host.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable frame-tweaks-tray-host.service
# (a failed unit's record cleared, so a reinstall starts it again whatever happened to it before)
sysctl_user reset-failed frame-tweaks-tray-host.service 2>/dev/null || true
# (enable alone starts it with the next VR session; this one may be running already)
if sysctl_user is-active --quiet gamescope-session.target; then
    sysctl_user restart frame-tweaks-tray-host.service || true
    if sysctl_user is-active --quiet frame-tweaks-tray-host.service; then
        say "$(t 'Tray icons in the VR session get an answer now')"
    else
        warn "$(t "%s didn't start; see: %s" frame-tweaks-tray-host "systemctl --user status frame-tweaks-tray-host")"
    fi
else
    say "$(t 'It starts with the VR session')"
fi
