#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/speech"
C="$HOME/.config/speech-dispatcher"
restore_file speech "$C/speechd.conf"
restore_file speech "$C/modules/espeak-ng.conf"
pkill -u "$(id -u)" -x speech-dispatcher 2>/dev/null || true
remove_files "$D"
say "speech-dispatcher is back to SteamOS's setup (no voice)."
