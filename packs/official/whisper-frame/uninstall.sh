#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
sysctl_user disable --now whisper-ptt whisper-panel 2>/dev/null || true
remove_files "$BIN/whisper-ptt" "$BIN/whisper-panel" "$HOME/.local/lib/whisper-frame" \
    "$HOME/.config/systemd/user/whisper-ptt.service" "$HOME/.config/systemd/user/whisper-panel.service" \
    "$HOME/.config/systemd/user/whisper-panel.service.d"
sysctl_user daemon-reload || true
if [ -x "$BIN/dictate" ]; then
    say "Kept the Whisper model: dictation uses it. Re-run ./install.sh dictation to switch it to Homebrew's whisper.cpp."
else
    remove_files "$HOME/.local/share/whisper/ggml-small-q8_0.bin"
fi
