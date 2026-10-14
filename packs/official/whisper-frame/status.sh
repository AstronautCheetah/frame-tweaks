#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/whisper-ptt" ] || status_missing "whisper-frame not installed"
sysctl_user is-active --quiet whisper-ptt || status_warn "whisper-ptt not running"
mic=$(sysctl_user is-active --quiet whisper-panel && echo " + window mic" || echo " (window mic off)")
status_ok "whisper-frame $(cat "$HOME/.local/lib/whisper-frame/VERSION" 2>/dev/null): Select button$mic"
