#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
f="$HOME/.config/environment.d/90-kwin-software-cursor.conf"
[ -f "$f" ] || status_missing "cursor fix not installed"
[ "${KWIN_FORCE_SW_CURSOR:-}" = 1 ] || status_warn "installed; active after the next reboot"
status_ok "software cursor active"
