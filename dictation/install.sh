#!/bin/bash
# Local Whisper speech-to-text: one shortcut to record, then text is typed + copied.
source "$(dirname "$0")/../lib/common.sh"
ensure_path

# Engine: whisper-frame's bundled GPU whisper-cli if installed, else Homebrew's whisper-cpp.
# wl-clipboard (copy to the clipboard) from Homebrew either way.
WF_CLI="$HOME/.local/lib/whisper-frame/whisper-cli"
if [ -x "$WF_CLI" ]; then
    say "Using whisper-frame's whisper-cli (no second copy)"
    command -v wl-copy >/dev/null || { need_brew; brew install wl-clipboard; }
else
    need_brew
    say "Installing whisper.cpp and wl-clipboard (Homebrew)"
    brew install whisper-cpp wl-clipboard
fi

[ -x "$BIN/ydotoold" ] && [ -S "/run/user/$(id -u)/.ydotool_socket" ] ||
    "$REPO_DIR/ydotool/install.sh"

# Model: the same file whisper-frame uses, so installing both never keeps two copies.
MODELS="$HOME/.local/share/whisper"; MODEL=ggml-small-q8_0.bin
mkdir -p "$MODELS"
if [ ! -f "$MODELS/$MODEL" ]; then
    say "Downloading Whisper model $MODEL (shared with whisper-frame)"
    curl -fL# -o "$MODELS/$MODEL.part" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$MODEL"
    mv "$MODELS/$MODEL.part" "$MODELS/$MODEL"
fi
# Models older versions downloaded; the shared one replaces them.
for old in ggml-small.en-q5_1.bin ggml-base.en-q5_1.bin; do
    if [ -f "$MODELS/$old" ] && ! grep -qs "$old" "$HOME/.config/dictate.conf"; then
        rm -f "$MODELS/$old" && say "Removed old model $old (replaced by the shared $MODEL)"
    fi
done

install -m755 "$REPO_DIR/dictation/dictate" "$BIN/dictate"
install_icon frame-tweaks-dictate
install_desktop "$REPO_DIR/dictation/dictate.desktop"
[ -f "$HOME/.config/dictate.conf" ] || cp "$REPO_DIR/dictation/dictate.conf.example" "$HOME/.config/dictate.conf"

say "Done. Bind 'Dictate (toggle)' to a key in System Settings → Keyboard → Shortcuts."
