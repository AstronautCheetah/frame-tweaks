#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/ydotoold" ] || status_missing "$(t '%s not installed' ydotool)"
sysctl_user is-active --quiet ydotoold || status_warn "$(t '%s service not running (%s)' ydotoold "systemctl --user start ydotoold")"
[ -S "/run/user/$(id -u)/.ydotool_socket" ] || status_warn "$(t '%s socket missing' ydotoold)"
status_ok "$(t '%s running' ydotoold)"
