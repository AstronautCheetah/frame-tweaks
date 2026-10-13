#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/snip"
[ -x "$BIN/frame-snip" ] || status_missing "not installed"
command -v tesseract >/dev/null || [ -x /home/linuxbrew/.linuxbrew/bin/tesseract ] ||
    status_warn "Tesseract missing: Copy text and Narrate won't work (reinstall)"
{ [ -x "$D/piper/piper" ] && [ -f "$D/voice.onnx" ]; } || status_warn "Piper or its voice missing: Narrate won't work (reinstall)"
status_ok "snip ready (copy, save, copy text, narrate)"
