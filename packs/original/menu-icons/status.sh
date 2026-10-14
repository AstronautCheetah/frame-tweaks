#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/menu-icons"
[ -x "$D/menu-icons" ] || status_missing "$(t 'not installed')"
n=$("$D/menu-icons" status 2>/dev/null) || true
status_ok "$(t '%s icon(s) added for the "+" menu' "${n:-0}")"
