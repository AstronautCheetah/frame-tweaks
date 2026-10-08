#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/curvature"
U="$HOME/.config/systemd/user"
sysctl_user stop sft-curvature.service 2>/dev/null || true
# Unpatch the running dashboard (windows keep their current curvature).
[ -x "$D/sft-curvature" ] && python3 - "$D" <<'PY' 2>/dev/null || true
import importlib.machinery, sys
m = importlib.machinery.SourceFileLoader("c", sys.argv[1] + "/sft-curvature").load_module()
u = m.systemui()
u and m.ws_eval(u, "window.__sftCurvature?.stop?.(); delete window.__sftCurvature")
PY
# The port setting goes back as it was when SteamVR next stops (or now, if it isn't running).
sysctl_user is-active --quiet steamvr.service || "$D/sft-curvature" restore 2>/dev/null || true
if [ -f "$HOME/.local/state/steam-frame-tweaks/vr-debugger.prev" ] && sysctl_user is-active --quiet steamvr.service; then
    # Keep only the restore step until SteamVR stops; it removes itself afterwards.
    install -m755 "$D/sft-curvature" "$HOME/.local/state/steam-frame-tweaks/sft-curvature-restore"
    printf '[Service]\nExecStopPost=-%s restore\nExecStopPost=-/bin/rm -f %s %s\n' \
        "$HOME/.local/state/steam-frame-tweaks/sft-curvature-restore" \
        "$U/steamvr.service.d/sft-curvature.conf" "$HOME/.local/state/steam-frame-tweaks/sft-curvature-restore" \
        > "$U/steamvr.service.d/sft-curvature.conf"
    remove_files "$D" "$U/sft-vr-debugger.service" "$U/sft-curvature.service"
else
    remove_files "$D" "$U/sft-vr-debugger.service" "$U/sft-curvature.service" "$U/steamvr.service.d/sft-curvature.conf"
fi
sysctl_user daemon-reload
