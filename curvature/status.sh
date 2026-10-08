#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/curvature"
[ -x "$D/sft-curvature" ] && [ -f "$HOME/.config/systemd/user/steamvr.service.d/sft-curvature.conf" ] ||
    status_missing "not installed"
sysctl_user is-active --quiet steamvr.service || status_ok "installed (active while SteamVR runs)"
s=$(timeout 8 "$D/sft-curvature" status 2>/dev/null) || true
case "$s" in
    patched) status_ok "world windows start curved" ;;
    port*closed*) status_warn "waiting for a SteamVR restart (reboot once)" ;;
    *) status_warn "${s:-not responding}" ;;
esac
