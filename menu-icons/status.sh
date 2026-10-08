#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/menu-icons"
[ -x "$D/menu-icons" ] || status_missing "not installed"
n=$("$D/menu-icons" status 2>/dev/null) || true
status_ok "${n:-0} icon(s) added for the \"+\" menu"
