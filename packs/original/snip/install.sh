#!/bin/bash
# Screen snip: select a rectangle of the window you're using, then copy it, save it, copy its
# text (Tesseract OCR) or read it aloud (Piper, from the speech helper). Arrow Pad's Tools layer
# and the app menu start it.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"

# The selection window uses PyQt6 (shared with Arrow Pad and the NordVPN tray).
if ! "$QT_VENV/bin/python" -c 'import PyQt6' 2>/dev/null; then
    say "Setting up PyQt6 (shared with Arrow Pad)"
    python3 -m venv "$QT_VENV"
    pip_pinned "$QT_VENV" PyQt6 || die "couldn't install PyQt6"
fi

# The narration panel is its own SteamVR overlay (like Arrow Pad): the openvr bindings, on
# SteamVR's own arm64 library (the wheel only bundles an x86 one). Without them it's a window.
ensure_openvr "$QT_VENV" || true

# OCR: Tesseract from Homebrew (with its English data).
need_brew
brew list tesseract >/dev/null 2>&1 || { say "Installing Tesseract (OCR)"; brew install tesseract || die "brew install tesseract failed"; }
# Copy text, the narration panel's Paste and the image-copy fallback use wl-copy / wl-paste.
command -v wl-copy >/dev/null || brew list wl-clipboard >/dev/null 2>&1 ||
    { say "Installing wl-clipboard"; brew install wl-clipboard || die "brew install wl-clipboard failed"; }

# Narrate: Piper and its voice come from the Speech engine helper (speech/).
[ -x "$HOME/.local/share/frame-tweaks/speech/piper/piper" ] || "$(tweak_dir speech)/install.sh"

ensure_path
sed "1s|.*|#!$QT_VENV/bin/python|" "$TWEAK_DIR/frame-snip" | write_file "$BIN/frame-snip" 755
install_icon frame-tweaks-snip
install_desktop "$TWEAK_DIR/frame-snip.desktop"
# (0.4.1 briefly floated the selection over a floating window: less usable than snipping its copy
# in the dashboard. Remove that patch if it's there.)
[ -f "$VR_DASHBOARD/patches/snip-float.js" ] && remove_dashboard_patch snip-float
say "Done: Arrow Pad's Tools key, then Snip (or 'Screen snip + Narrate' in the app menu) starts a snip."
