#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_icon frame-tweaks-dictate
remove_desktop dictate.desktop
sysctl_user disable --now frame-tweaks-dictate-button.service 2>/dev/null || true
sysctl_user stop frame-tweaks-dictate-engine.service 2>/dev/null || true
remove_files "$BIN/dictate" "$BIN/dictate-button" "$BIN/dictate-menu" "$BIN/dictate-parakeet" \
    "$HOME/.config/systemd/user/frame-tweaks-dictate-button.service" \
    "$HOME/.config/systemd/user/frame-tweaks-dictate-engine.service" \
    "$HOME/.local/share/whisper/ggml-silero-v6.2.0.bin" "$HOME/.local/share/frame-tweaks/parakeet"
sysctl_user daemon-reload || true
settings_unapplied
if [ -x "$BIN/whisper-ptt" ]; then
    say "$(t 'Kept the Whisper model: whisper-frame uses it too.')"
else
    remove_files "$HOME/.local/share/whisper/ggml-small-q8_0.bin"
fi
say "$(t 'Kept your dictation history (~/.local/share/dictation-history.txt); whisper-cpp (if any) stays in Homebrew.')"
