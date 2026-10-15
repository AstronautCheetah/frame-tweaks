#!/bin/bash
# Arrow Pad: no-focus nav pad (arrows, one-shot modifiers, F-keys, clipboard, 🎤 dictation).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path

[ -x "$BIN/ydotoold" ] && [ -S "/run/user/$(id -u)/.ydotool_socket" ] ||
    "$(tweak_dir ydotool)/install.sh"

VENV=$QT_VENV
ensure_qt_venv || die "$(t "couldn't install PyQt6")"
install_i18n         # (Arrow Pad's text in your language)
install -m644 "$TWEAK_DIR/arrowpad.py" "$HOME/.local/share/arrowpad/arrowpad.py"
install -m644 "$TWEAK_DIR/haptics.py" "$HOME/.local/share/arrowpad/haptics.py"
install -m644 "$TWEAK_DIR/vroverlay.py" "$HOME/.local/share/arrowpad/vroverlay.py"
mkdir -p "$HOME/.local/share/arrowpad/vr"
install -m644 "$TWEAK_DIR"/vr/*.json "$HOME/.local/share/arrowpad/vr/"

# Controller haptics: SteamVR Input through the openvr bindings, using SteamVR's own
# arm64 library (the wheel only bundles an x86 one).
if ! ensure_openvr "$VENV"; then
    warn "$(t "SteamVR's arm64 OpenVR library not found: Arrow Pad works without controller haptics.")"
fi
write_file "$BIN/arrowpad" 755 <<EOS
#!/bin/sh
exec "$VENV/bin/python" "$HOME/.local/share/arrowpad/arrowpad.py" "\$@"
EOS
install_icon frame-tweaks-arrowpad
install_desktop "$TWEAK_DIR/arrowpad.desktop"
install_desktop "$TWEAK_DIR/arrowpad-vr.desktop"
say "$(t "Done. Launch 'Arrow Pad' from the app menu (or: arrowpad --scale 1.5).")"
