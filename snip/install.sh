#!/bin/bash
# Screen snip: select a rectangle of the window you're using, then copy it, save it, copy its
# text (Tesseract OCR) or read it aloud (Piper). Arrow Pad's ✂ button and the app menu start it.
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/snip"
mkdir -p "$D"

# The selection window uses PyQt6 (shared with Arrow Pad and the NordVPN tray).
if ! "$QT_VENV/bin/python" -c 'import PyQt6' 2>/dev/null; then
    say "Setting up PyQt6 (shared with Arrow Pad)"
    python3 -m venv "$QT_VENV"
    "$QT_VENV/bin/pip" install -q -c "$REPO_DIR/lib/python-constraints.txt" PyQt6 || die "couldn't install PyQt6"
fi

# OCR: Tesseract from Homebrew (with its English data).
need_brew
brew list tesseract >/dev/null 2>&1 || { say "Installing Tesseract (OCR)"; brew install tesseract || die "brew install tesseract failed"; }

# Narrate: Piper (pinned build) and a public-domain voice (pinned files).
if [ ! -x "$D/piper/piper" ] || [ "$(cat "$D/piper/.version" 2>/dev/null)" != "$(pin_version snip)" ]; then
    say "Downloading Piper (speech)"
    t=$(mktemp -d)
    fetch_pinned snip "$t/piper.tgz"
    rm -rf "$D/piper" && tar -xzf "$t/piper.tgz" -C "$D" && rm -rf "$t"
    [ -x "$D/piper/piper" ] || die "the Piper download didn't contain piper/piper"
    pin_version snip > "$D/piper/.version"
fi
voice_rev=$(sed -n 's/^version=//p' "$REPO_DIR/snip/voice.pin")
if [ "$(cat "$D/voice.version" 2>/dev/null)" != "$voice_rev" ]; then
    say "Downloading the voice (about 60 MB)"
    fetch_pinned snip "$D/voice.onnx.part" voice.pin && mv "$D/voice.onnx.part" "$D/voice.onnx"
    fetch_pinned snip "$D/voice.onnx.json.part" voice-config.pin && mv "$D/voice.onnx.json.part" "$D/voice.onnx.json"
    echo "$voice_rev" > "$D/voice.version"
fi

ensure_path
sed "1s|.*|#!$QT_VENV/bin/python|" "$REPO_DIR/snip/frame-snip" > "$BIN/frame-snip"
chmod 755 "$BIN/frame-snip"
install_icon frame-tweaks-snip
install_desktop "$REPO_DIR/snip/frame-snip.desktop"
say "Done: Arrow Pad's ✂ button (or 'Screen snip' in the app menu) starts a snip."
