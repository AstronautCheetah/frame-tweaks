#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/speech"
[ -x "$BIN/frame-snip" ] || status_missing "$(t 'not installed')"
command -v tesseract >/dev/null || [ -x /home/linuxbrew/.linuxbrew/bin/tesseract ] ||
    status_warn "$(t "Tesseract missing: Copy text and Narrate won't work (reinstall)")"
{ [ -x "$D/piper/piper" ] && [ -f "$D/voice.onnx" ]; } || status_warn "$(t "Piper or its voice missing: Narrate won't work (reinstall)")"
status_ok "$(t 'snip ready (copy, save, copy text, narrate)')"
