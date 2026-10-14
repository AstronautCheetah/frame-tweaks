#!/bin/bash
# Arrow Pad: no-focus nav pad (arrows, one-shot modifiers, F-keys, clipboard, 🎤 dictation).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path

[ -x "$BIN/ydotoold" ] && [ -S "/run/user/$(id -u)/.ydotool_socket" ] ||
    "$(tweak_dir ydotool)/install.sh"

VENV="$HOME/.local/share/arrowpad/venv"
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c 'import PyQt6' 2>/dev/null; then
    say "Creating Python venv with PyQt6 (~280 MB)"
    python3 -m venv "$VENV"
    pip_pinned "$VENV" PyQt6
fi
install -m644 "$TWEAK_DIR/arrowpad.py" "$HOME/.local/share/arrowpad/arrowpad.py"
install -m644 "$TWEAK_DIR/haptics.py" "$HOME/.local/share/arrowpad/haptics.py"
install -m644 "$TWEAK_DIR/vroverlay.py" "$HOME/.local/share/arrowpad/vroverlay.py"
mkdir -p "$HOME/.local/share/arrowpad/vr"
install -m644 "$TWEAK_DIR"/vr/*.json "$HOME/.local/share/arrowpad/vr/"

# Controller haptics: SteamVR Input through the openvr bindings, using SteamVR's own
# arm64 library (the wheel only bundles an x86 one).
if ! ensure_openvr "$VENV"; then
    warn "SteamVR's arm64 OpenVR library not found: Arrow Pad works without controller haptics."
fi
cat > "$BIN/arrowpad" <<EOS
#!/bin/sh
exec "$VENV/bin/python" "$HOME/.local/share/arrowpad/arrowpad.py" "\$@"
EOS
chmod +x "$BIN/arrowpad"
install_icon frame-tweaks-arrowpad
install_desktop "$TWEAK_DIR/arrowpad.desktop"
install_desktop "$TWEAK_DIR/arrowpad-vr.desktop"
say "Done. Launch 'Arrow Pad' from the app menu (or: arrowpad --scale 1.5)."
