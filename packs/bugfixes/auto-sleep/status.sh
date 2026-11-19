#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNIT=frame-tweaks-auto-sleep.service
[ -x "$BIN/frame-tweaks-auto-sleep" ] && [ -f "$HOME/.config/systemd/user/$UNIT" ] || status_missing "$(t 'not installed')"
sysctl_user is-active --quiet "$UNIT" || status_warn "$(t 'service not running (%s)' "journalctl --user -u $UNIT")"
status_ok "$("$BIN/frame-tweaks-auto-sleep" --status)"
