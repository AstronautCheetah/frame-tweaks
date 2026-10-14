#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/dictate" ] || status_missing "dictate not installed"
[ -x "$HOME/.local/lib/whisper-frame/whisper-cli" ] || command -v whisper-cli >/dev/null ||
    [ -x /home/linuxbrew/.linuxbrew/bin/whisper-cli ] || status_warn "no whisper-cli (re-run ./install.sh dictation)"
[ -f "$HOME/.local/share/whisper/ggml-small-q8_0.bin" ] || grep -qs '^DICTATE_MODEL=' "$HOME/.config/frame-tweaks/dictate.conf" ||
    status_warn "Whisper model missing (re-run ./install.sh dictation)"
engine=$([ -x "$HOME/.local/lib/whisper-frame/whisper-cli" ] && echo "whisper-frame's engine" || echo "Homebrew whisper.cpp")
status_ok "dictate ready ($engine, shared small model)"
