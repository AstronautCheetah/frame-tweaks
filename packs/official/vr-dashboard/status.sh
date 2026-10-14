#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/vr-dashboard"
[ -x "$D/sft-dashboard" ] && [ -f "$HOME/.config/systemd/user/steamvr.service.d/sft-dashboard.conf" ] ||
    status_missing "not installed"
n=$(find "$D/patches" -name '*.js' 2>/dev/null | wc -l)
sysctl_user is-active --quiet steamvr.service || status_ok "installed, $n patch(es) (active while SteamVR runs)"
s=$(timeout 8 "$D/sft-dashboard" status 2>/dev/null | head -1) || true
case "$s" in
    *port*closed*) status_warn "waiting for a SteamVR restart (reboot once)" ;;
    *changed*) status_warn "$s" ;;
esac
status_ok "$n dashboard patch(es); DevTools port open while SteamVR runs"
