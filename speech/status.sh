#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/speech"
{ [ -x "$D/piper/piper" ] && [ -f "$D/voice.onnx" ]; } || status_missing "not installed"
grep -qs "$D/sd_espeak-ng" "$HOME/.config/speech-dispatcher/speechd.conf" ||
    status_warn "speech-dispatcher isn't set up (Orca has no voice): reinstall"
status_ok "Piper voice ready; speech-dispatcher uses espeak-ng"
