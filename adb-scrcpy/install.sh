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

install -m755 "$REPO_DIR/adb-scrcpy/phone" "$BIN/phone"
install_icon frame-tweaks-phone
# Renamed from "Phone Mirror" (it only works with Android). Keep a password gate if it had one.
gated=""
grep -qs wallet-gate "$APPS/phone-mirror.desktop" && gated=1
rm -f "$APPS/phone-mirror.desktop" "$LAUNCHER_ORIGINALS/phone-mirror.desktop"
install_desktop "$REPO_DIR/adb-scrcpy/android-mirror.desktop"
if [ -n "$gated" ] && [ -x "$BIN/wallet-launcher" ]; then "$BIN/wallet-launcher" --gate --no-shared android-mirror; fi
cat <<MSG
Done. One-time pairing: on the phone open Developer options → Wireless debugging →
"Pair device with pairing code", then within the minute run:
    adb pair <ip>:<pairing-port> <code>
Afterwards just launch 'Android Mirror' (or run: phone).
MSG
