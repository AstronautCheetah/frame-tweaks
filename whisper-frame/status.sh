#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/whisper-ptt" ] || status_missing "whisper-frame not installed"
sysctl_user is-active --quiet whisper-ptt || status_warn "whisper-ptt not running"
sysctl_user is-active --quiet whisper-panel || status_warn "window mic (whisper-panel) not running"
status_ok "whisper-frame $(cat "$HOME/.local/lib/whisper-frame/VERSION" 2>/dev/null): Select button + window mic"
