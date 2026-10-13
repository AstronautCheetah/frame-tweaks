#!/bin/bash
# Arrow Pad: no-focus nav pad (arrows, one-shot modifiers, F-keys, clipboard, 🎤 dictation).
source "$(dirname "$0")/../lib/common.sh"
ensure_path

[ -x "$BIN/ydotoold" ] && [ -S "/run/user/$(id -u)/.ydotool_socket" ] ||
    "$REPO_DIR/ydotool/install.sh"

VENV="$HOME/.local/share/arrowpad/venv"
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" -c 'import PyQt6' 2>/dev/null; then
    say "Creating Python venv with PyQt6 (~280 MB)"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade -c "$REPO_DIR/lib/python-constraints.txt" PyQt6
fi
install -m644 "$REPO_DIR/arrowpad/arrowpad.py" "$HOME/.local/share/arrowpad/arrowpad.py"
install -m644 "$REPO_DIR/arrowpad/haptics.py" "$HOME/.local/share/arrowpad/haptics.py"
install -m644 "$REPO_DIR/arrowpad/vroverlay.py" "$HOME/.local/share/arrowpad/vroverlay.py"
mkdir -p "$HOME/.local/share/arrowpad/vr"
install -m644 "$REPO_DIR"/arrowpad/vr/*.json "$HOME/.local/share/arrowpad/vr/"

# Controller haptics: SteamVR Input through the openvr bindings, using SteamVR's own
# arm64 library (the wheel only bundles an x86 one).
VR_LIB=/opt/steamvr/bin/linuxarm64/libopenvr_api.so
if [ -f "$VR_LIB" ]; then
    "$VENV/bin/python" -c 'import importlib.util,sys; sys.exit(0 if importlib.util.find_spec("openvr") else 1)' ||
        "$VENV/bin/pip" install -q -c "$REPO_DIR/lib/python-constraints.txt" openvr
    OVR=$("$VENV/bin/python" -c 'import importlib.util,os; print(os.path.dirname(importlib.util.find_spec("openvr").origin))')
    ln -sf "$VR_LIB" "$OVR/libopenvr_api_64.so"
else
    warn "SteamVR's arm64 OpenVR library not found: Arrow Pad works without controller haptics."
fi
cat > "$BIN/arrowpad" <<EOS
#!/bin/sh
exec "$VENV/bin/python" "$HOME/.local/share/arrowpad/arrowpad.py" "\$@"
EOS
chmod +x "$BIN/arrowpad"
install_icon frame-tweaks-arrowpad
install_desktop "$REPO_DIR/arrowpad/arrowpad.desktop"
install_desktop "$REPO_DIR/arrowpad/arrowpad-vr.desktop"
say "Done. Launch 'Arrow Pad' from the app menu (or: arrowpad --scale 1.5)."
