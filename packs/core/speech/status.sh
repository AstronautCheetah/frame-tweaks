#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/speech"
{ [ -x "$D/piper/piper" ] && [ -f "$D/voice.onnx" ]; } || status_missing "$(t 'not installed')"
# (SteamOS 0.5.6 removed speech-dispatcher: then Piper is all there is to have)
[ -x "${FRAME_TWEAKS_SPEECHD_ROOT:-}/usr/lib/speech-dispatcher/speech-dispatcher-modules/sd_espeak-ng" ] ||
    status_ok "$(t 'Piper voice ready (this SteamOS has no speech-dispatcher)')"
grep -qs "$D/sd_espeak-ng" "$HOME/.config/speech-dispatcher/speechd.conf" ||
    status_warn "$(t "speech-dispatcher isn't set up (Orca has no voice): reinstall")"
status_ok "$(t 'Piper voice ready; speech-dispatcher uses espeak-ng')"
