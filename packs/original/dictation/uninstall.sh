#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_icon frame-tweaks-dictate
remove_desktop dictate.desktop
remove_files "$BIN/dictate"
if [ -x "$BIN/whisper-ptt" ]; then
    say "$(t 'Kept the Whisper model: whisper-frame uses it too.')"
else
    remove_files "$HOME/.local/share/whisper/ggml-small-q8_0.bin"
fi
say "$(t 'Kept your dictation history (~/.local/share/dictation-history.txt); whisper-cpp (if any) stays in Homebrew.')"
