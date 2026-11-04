#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
APP="$HOME/Games/MoonlightXRNative/app"
[ -x "$APP/moonlight-xr" ] || status_missing "$(t 'not installed')"
ver=$(cat "$APP/VERSION" 2>/dev/null || true)
[ -f "$APPS/moonlight-xr.desktop" ] || status_warn "$(t 'its app-menu entry is missing (Reinstall adds it)')"
status_ok "$(t 'Moonlight XR for Frame %s' "${ver:-?}")"
