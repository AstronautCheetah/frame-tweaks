#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
"$BIN/adb" kill-server 2>/dev/null || true
remove_files "$ICONS/256x256/apps/frame-tweaks-phone.png" "$BIN/adb" "$BIN/phone" "$HOME/.local/lib/android-tools" "$APPS/android-mirror.desktop" "$APPS/phone-mirror.desktop" "$LAUNCHER_ORIGINALS/android-mirror.desktop"
say "Kept ~/.config/phone.conf, adb pairing keys (~/.android) and scrcpy (brew uninstall scrcpy)."
