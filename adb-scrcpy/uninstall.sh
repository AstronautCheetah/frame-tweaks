#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
remove_dashboard_patch phone-rotate
remove_dashboard_patch phone-touch
"$BIN/adb" kill-server 2>/dev/null || true
remove_files "$ICONS/256x256/apps/frame-tweaks-phone.png" "$BIN/adb" "$BIN/phone" "$BIN/phone-fit" "$BIN/phone-touch" "$HOME/.local/lib/android-tools" "$APPS/android-mirror.desktop" "$APPS/phone-mirror.desktop" "$LAUNCHER_ORIGINALS/android-mirror.desktop"
say "Kept ~/.config/phone.conf, adb pairing keys (~/.android) and scrcpy (brew uninstall scrcpy)."
