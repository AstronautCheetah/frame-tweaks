#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/speech"
C="$HOME/.config/speech-dispatcher"
restore_file speech "$C/speechd.conf"
restore_file speech "$C/modules/espeak-ng.conf"
pkill -u "$(id -u)" -x speech-dispatcher 2>/dev/null || true
remove_files "$D"
[ -x "${FRAME_TWEAKS_SPEECHD_ROOT:-}/usr/lib/speech-dispatcher/speech-dispatcher-modules/sd_espeak-ng" ] &&
    say "$(t "speech-dispatcher is back to SteamOS's setup (no voice).")"
exit 0
