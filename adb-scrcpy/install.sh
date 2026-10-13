#!/bin/bash
# adb (aarch64 build from Arch Linux ARM; Google ships x86 only) + scrcpy + 'phone' launcher.
source "$(dirname "$0")/../lib/common.sh"
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
rm -rf "$LIB" && mkdir -p "$LIB"
cp -a "$T"/deps/usr/lib/*.so* "$LIB/"
install -m755 "$T/at/usr/bin/adb" "$LIB/adb.bin"
cat > "$BIN/adb" <<'EOS'
#!/bin/sh
LD_LIBRARY_PATH="$HOME/.local/lib/android-tools${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" exec "$HOME/.local/lib/android-tools/adb.bin" "$@"
EOS
chmod +x "$BIN/adb"
missing=$(LD_LIBRARY_PATH="$LIB" ldd "$LIB/adb.bin" | grep 'not found' || true)
[ -z "$missing" ] || die "adb still has missing libraries:\n$missing"
"$BIN/adb" version | sed -n 1,2p

install -m755 "$REPO_DIR/adb-scrcpy/phone" "$REPO_DIR/adb-scrcpy/phone-fit" "$BIN/"
# phone-touch reads the joystick through SteamVR (openvr): it runs on the shared venv.
ensure_tweaks_venv
ensure_openvr "$TWEAKS_VENV" || say "SteamVR's OpenVR library not found: no joystick scrolling on the mirror."
install_py_tool "$REPO_DIR/adb-scrcpy/phone-touch"
install_icon frame-tweaks-phone
# Renamed from "Phone Mirror" (it only works with Android). Keep a password gate if it had one.
gated=""
grep -qs wallet-gate "$APPS/phone-mirror.desktop" && gated=1
rm -f "$APPS/phone-mirror.desktop" "$LAUNCHER_ORIGINALS/phone-mirror.desktop"
install_desktop "$REPO_DIR/adb-scrcpy/android-mirror.desktop"
if [ -n "$gated" ] && [ -x "$BIN/wallet-launcher" ]; then "$BIN/wallet-launcher" --gate --no-shared android-mirror; fi
# In VR, turning the phone turns the window without shrinking it (a dashboard patch; needs the
# VR windows helper, which the VR windows tweaks install).
if [ -x "$VR_DASHBOARD/sft-dashboard" ]; then
    install_dashboard_patch phone-rotate "$REPO_DIR/adb-scrcpy/patch.js"
    # ... and laser clicks on it land where you aim (see phone-touch).
    install_dashboard_patch phone-touch "$REPO_DIR/adb-scrcpy/phone-touch.js"
else
    say "In VR, the window keeps its width when the phone turns, and clicks on an upright phone land at its left edge (install a VR windows tweak to fix both)."
fi
cat <<MSG
Done. One-time pairing: on the phone open Developer options → Wireless debugging →
"Pair device with pairing code", then within the minute run:
    adb pair <ip>:<pairing-port> <code>
Afterwards just launch 'Android Mirror' (or run: phone).
MSG
