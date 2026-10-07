#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/dictate" ] || status_missing "dictate not installed"
command -v whisper-cli >/dev/null || [ -x /home/linuxbrew/.linuxbrew/bin/whisper-cli ] || status_warn "whisper-cli missing (brew install whisper-cpp)"
ls "$HOME"/.local/share/whisper/ggml-*.bin >/dev/null 2>&1 || status_warn "no Whisper model in ~/.local/share/whisper"
status_ok "dictate ready ($(ls "$HOME"/.local/share/whisper/ggml-*.bin | wc -l) model(s))"
