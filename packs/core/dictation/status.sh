#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/dictate" ] || status_missing "$(t 'dictate not installed')"
[ -x "$HOME/.local/lib/whisper-frame/whisper-cli" ] || brew_cmd whisper-cli >/dev/null || status_warn "$(t 'no whisper-cli (re-run ./install.sh dictation)')"
[ -f "$HOME/.local/share/whisper/ggml-small-q8_0.bin" ] || grep -qs '^DICTATE_MODEL=' "$HOME/.config/frame-tweaks/dictate.conf" ||
    status_warn "$(t 'Whisper model missing (re-run ./install.sh dictation)')"
engine=$([ -x "$HOME/.local/lib/whisper-frame/whisper-cli" ] && t "whisper-frame's engine" || echo "Homebrew whisper.cpp")
# shellcheck source=button-names.sh
source "$TWEAK_DIR/button-names.sh"
button=$(dictate_button)
if [ -x "$BIN/dictate-button" ]; then
    [ "$button" != off ] || status_ok "$(t 'dictate ready (%s, small model); no controller button (⚙ Settings)' "$engine")"
    if sysctl_user is-active --quiet steamvr.service && ! sysctl_user is-active --quiet frame-tweaks-dictate-button.service; then
        status_warn "$(t "the controller button isn't running (re-run ./install.sh dictation)")"
    fi
    status_ok "$(t 'dictate ready (%s, small model); hold %s to dictate' "$engine" "$(button_name "$button")")"
fi
status_ok "$(t 'dictate ready (%s, small model)' "$engine")"
