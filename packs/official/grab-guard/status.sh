#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/grab-guard" ] || status_missing "not installed"
sysctl_user is-active --quiet grab-guard || status_warn "installed but not running (systemctl --user start grab-guard)"
"$BIN/grab-guard" --status 2>/dev/null | head -1 | grep -q "^GRABBED" &&
    status_warn "desktop mode has taken all input: tap Right Ctrl on a keyboard once"
status_ok "watching for desktop mode taking all input"
