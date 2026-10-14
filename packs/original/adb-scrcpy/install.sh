#!/bin/bash
# adb (aarch64 build from Arch Linux ARM; Google ships x86 only) + scrcpy + 'phone' launcher.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
need_brew
ensure_path

say "Installing scrcpy (Homebrew)"
brew install scrcpy

# adb plus the libraries SteamOS lacks or has too old, kept private to adb.
LIB="$HOME/.local/lib/android-tools"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
alarm_fetch extra android-tools "$T/at"
for p in "extra protobuf" "extra fmt" "extra abseil-cpp" "core libusb"; do
    alarm_fetch $p "$T/deps"
done
NEW="$T/lib"; mkdir -p "$NEW"
cp -a "$T"/deps/usr/lib/*.so* "$NEW/"
install -m755 "$T/at/usr/bin/adb" "$NEW/adb.bin"
# Swapped in only if it runs here; otherwise a working adb from before is kept.
if missing=$(runs_here "$NEW/adb.bin" "$NEW") && LD_LIBRARY_PATH="$NEW" "$NEW/adb.bin" version >/dev/null 2>&1; then
    # (Copied beside it, then swapped by rename: a failed copy leaves the old one working.)
    rm -rf "$LIB.new" "$LIB.old" && mkdir -p "$(dirname "$LIB")" && cp -a "$NEW" "$LIB.new" &&
        { [ ! -e "$LIB" ] || mv "$LIB" "$LIB.old"; } && mv "$LIB.new" "$LIB" && rm -rf "$LIB.old" ||
        die "couldn't put the new adb in place (the one before is in $LIB or $LIB.old)"
elif [ -x "$LIB/adb.bin" ] && LD_LIBRARY_PATH="$LIB" "$LIB/adb.bin" version >/dev/null 2>&1; then
    warn "Arch Linux ARM's current adb doesn't run on this SteamOS; keeping the adb you have. Missing: $missing"
else
    die "Arch Linux ARM's current adb doesn't run on this SteamOS. Missing: $missing"
fi
# adb's server listens on a socket file in your runtime folder instead of TCP 127.0.0.1:5037,
# which every local program (sandboxed Flatpak apps too) could use to get a shell on a connected
# phone. (Set ADB_SERVER_SOCKET yourself to override.) An old server on the TCP port is stopped.
ADB_SERVER_SOCKET=tcp:localhost:5037 LD_LIBRARY_PATH="$LIB" timeout 10 "$LIB/adb.bin" kill-server 2>/dev/null || true
write_file "$BIN/adb" 755 <<'EOS'
#!/bin/sh
: "${ADB_SERVER_SOCKET:=localfilesystem:${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/adb.sock}"
export ADB_SERVER_SOCKET
LD_LIBRARY_PATH="$HOME/.local/lib/android-tools${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" exec "$HOME/.local/lib/android-tools/adb.bin" "$@"
EOS
"$BIN/adb" version | sed -n 1,2p

install -m755 "$TWEAK_DIR/phone" "$TWEAK_DIR/phone-fit" "$BIN/"
# phone-touch reads the joystick through SteamVR (openvr): it runs on the shared venv.
ensure_tweaks_venv
ensure_openvr "$TWEAKS_VENV" || say "SteamVR's OpenVR library not found: no joystick scrolling on the mirror."
install_py_tool "$TWEAK_DIR/phone-touch"
install_icon frame-tweaks-phone
# Renamed from "Phone Mirror" (it only works with Android). Keep a password gate if it had one.
gated=""
grep -qs wallet-gate "$APPS/phone-mirror.desktop" && gated=1
rm -f "$APPS/phone-mirror.desktop" "$LAUNCHER_ORIGINALS/phone-mirror.desktop"
install_desktop "$TWEAK_DIR/android-mirror.desktop"
if [ -n "$gated" ] && [ -x "$BIN/wallet-launcher" ]; then "$BIN/wallet-launcher" --gate --no-shared android-mirror; fi
# In VR, turning the phone turns the window without shrinking it (a dashboard patch; needs the
# VR environment helper, which the VR environment tweaks install).
if [ -x "$VR_DASHBOARD/sft-dashboard" ]; then
    install_dashboard_patch phone-rotate "$TWEAK_DIR/patch.js"
    # ... and laser clicks on it land where you aim (see phone-touch).
    install_dashboard_patch phone-touch "$TWEAK_DIR/phone-touch.js"
else
    say "In VR, the window keeps its width when the phone turns, and clicks on an upright phone land at its left edge (install a VR environment tweak to fix both)."
fi
cat <<MSG
Done. One-time pairing: on the phone open Developer options → Wireless debugging →
"Pair device with pairing code", then within the minute run:
    adb pair <ip>:<pairing-port> <code>
Afterwards just launch 'Android Mirror' (or run: phone).
MSG
