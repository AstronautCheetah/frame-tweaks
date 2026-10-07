#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/ydotoold" ] || status_missing "ydotool not installed"
sysctl_user is-active --quiet ydotoold || status_warn "ydotoold service not running (systemctl --user start ydotoold)"
[ -S "/run/user/$(id -u)/.ydotool_socket" ] || status_warn "ydotoold socket missing"
status_ok "ydotoold running"
