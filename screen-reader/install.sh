#!/bin/bash
# Turn on KDE's screen reader (Orca, part of SteamOS) for the desktop session.
source "$(dirname "$0")/../lib/common.sh"
command -v orca >/dev/null || die "Orca isn't installed on this SteamOS build."
save_kconfig screen-reader kaccessrc ScreenReader Enabled          # restored on uninstall
kwriteconfig6 --file kaccessrc --group ScreenReader --key Enabled true
say "Screen reader on: Orca starts with desktop mode (next time you open it)."
say "Toggle it any time with Meta+Alt+S, or System Settings → Accessibility → Screen Reader."
