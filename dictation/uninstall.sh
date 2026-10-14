#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
remove_files "$ICONS/256x256/apps/frame-tweaks-dictate.png" "$BIN/dictate" "$APPS/dictate.desktop"
if [ -x "$BIN/whisper-ptt" ]; then
    say "Kept the Whisper model: whisper-frame uses it too."
else
    remove_files "$HOME/.local/share/whisper/ggml-small-q8_0.bin"
fi
say "Kept ~/.config/frame-tweaks/dictate.conf and ~/.local/share/dictation-history.txt; whisper-cpp (if any) stays in Homebrew."
