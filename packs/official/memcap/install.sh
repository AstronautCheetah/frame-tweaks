#!/bin/bash
# Memory caps for heavy apps: Whisper (dictation), scrcpy (Android Mirror), VSCodium.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
install -m755 "$TWEAK_DIR/capped" "$BIN/capped"
CONF="$HOME/.config/frame-tweaks/memcap.conf"
mkdir -p "$(dirname "$CONF")"
[ -f "$CONF" ] || install -m644 "$TWEAK_DIR/memcap.conf" "$CONF"
get() { sed -n "s/^$1=//p" "$CONF" | tail -1; }
# Flatpak apps get their own systemd scope (app-flatpak-<id>-<pid>.scope); a prefix drop-in
# applies to every one of them.
D="$HOME/.config/systemd/user/app-flatpak-com.vscodium.codium-.scope.d"
mkdir -p "$D"
printf '[Scope]\nMemoryHigh=%s\nMemoryMax=%s\n' "$(get vscodium_high)" "$(get vscodium_max)" > "$D/memcap.conf"
sysctl_user daemon-reload
say "Caps: Whisper $(get whisper_max), scrcpy $(get scrcpy_max), VSCodium $(get vscodium_max) (edit $CONF)."
say "Dictation and Android Mirror pick them up at their next start; VSCodium at its next start."
