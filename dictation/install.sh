#!/bin/bash
# Local Whisper speech-to-text: one shortcut to record, then text is typed + copied.

source "$(dirname "$0")/../lib/common.sh"
need_brew
ensure_path

say "Installing whisper.cpp and wl-clipboard (Homebrew)"
brew install whisper-cpp wl-clipboard

[ -x "$BIN/ydotoold" ] && [ -S "/run/user/$(id -u)/.ydotool_socket" ] ||
    "$REPO_DIR/ydotool/install.sh"

MODELS="$HOME/.local/share/whisper"; mkdir -p "$MODELS"
for m in ${DICTATE_MODELS:-small.en-q5_1 base.en-q5_1}; do
    [ -f "$MODELS/ggml-$m.bin" ] && continue
    say "Downloading Whisper model $m"
    curl -fL# -o "$MODELS/ggml-$m.bin.part" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$m.bin"
    mv "$MODELS/ggml-$m.bin.part" "$MODELS/ggml-$m.bin"
done

install -m755 "$REPO_DIR/dictation/dictate" "$BIN/dictate"
install_desktop "$REPO_DIR/dictation/dictate.desktop"
[ -f "$HOME/.config/dictate.conf" ] || cp "$REPO_DIR/dictation/dictate.conf.example" "$HOME/.config/dictate.conf"

say "Done. Bind 'Dictate (toggle)' to a key in System Settings → Keyboard → Shortcuts."
