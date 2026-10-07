#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
remove_files "$BIN/dictate" "$APPS/dictate.desktop" "$HOME/.local/share/whisper"
say "Kept ~/.config/dictate.conf and ~/.local/share/dictation-history.txt; whisper-cpp stays in Homebrew (brew uninstall whisper-cpp)."
