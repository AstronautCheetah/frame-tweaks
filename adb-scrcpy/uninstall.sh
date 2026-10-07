#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
"$BIN/adb" kill-server 2>/dev/null || true
remove_files "$BIN/adb" "$BIN/phone" "$HOME/.local/lib/android-tools" "$APPS/phone-mirror.desktop"
say "Kept ~/.config/phone.conf, adb pairing keys (~/.android) and scrcpy (brew uninstall scrcpy)."
