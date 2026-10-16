#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_dashboard_patch phone-rotate
remove_dashboard_patch phone-touch
# Stop adb's servers: each session starts its own, its socket in that session's runtime folder
# (the adb wrapper, install.sh): VR's, and desktop mode's inside it (nested_plasma). Then the one
# this shell would use (your own ADB_SERVER_SOCKET, say).
vr_run=${XDG_RUNTIME_DIR:-$XDG_RUNTIME_DIR_USER}; vr_run=${vr_run%/nested_plasma}
for sock in "$vr_run/adb.sock" "$vr_run"/*/adb.sock; do
    [ -S "$sock" ] || continue
    ADB_SERVER_SOCKET="localfilesystem:$sock" "$BIN/adb" kill-server 2>/dev/null || true
done
"$BIN/adb" kill-server 2>/dev/null || true
remove_icon frame-tweaks-phone
remove_desktop android-mirror.desktop phone-mirror.desktop
remove_files "$BIN/adb" "$BIN/phone" "$BIN/phone-fit" "$BIN/phone-touch" "$HOME/.local/lib/android-tools" \
    "$HOME/.local/state/frame-tweaks/phone-touch-untested"
say "$(t "Kept adb's pairing keys (~/.android) and scrcpy (brew uninstall scrcpy).")"
