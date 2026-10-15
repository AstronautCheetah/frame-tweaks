#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_dashboard_patch phone-rotate
remove_dashboard_patch phone-touch
"$BIN/adb" kill-server 2>/dev/null || true
remove_icon frame-tweaks-phone
remove_desktop android-mirror.desktop phone-mirror.desktop
remove_files "$BIN/adb" "$BIN/phone" "$BIN/phone-fit" "$BIN/phone-touch" "$HOME/.local/lib/android-tools" \
    "$HOME/.local/state/frame-tweaks/phone-touch-untested"
say "$(t "Kept adb's pairing keys (~/.android) and scrcpy (brew uninstall scrcpy).")"
