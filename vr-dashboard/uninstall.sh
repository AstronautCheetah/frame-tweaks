#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/vr-dashboard"
U="$HOME/.config/systemd/user"
sysctl_user stop sft-dashboard.service 2>/dev/null || true
# Unpatch the running dashboard (windows stay as they are).
[ -x "$D/sft-dashboard" ] && python3 - "$D" <<'PY' 2>/dev/null || true
import importlib.machinery, importlib.util, sys
l = importlib.machinery.SourceFileLoader("d", sys.argv[1] + "/sft-dashboard")
m = importlib.util.module_from_spec(importlib.util.spec_from_loader("d", l)); l.exec_module(m)
u = m.systemui()
u and m.ws_eval(u, "for (const p of Object.values(window.__sftPatches ?? {})) p?.stop?.(); delete window.__sftPatches")
PY
# The port setting goes back as it was when SteamVR next stops (or now, if it isn't running).
sysctl_user is-active --quiet steamvr.service || "$D/sft-dashboard" restore 2>/dev/null || true
if [ -f "$HOME/.local/state/steam-frame-tweaks/vr-debugger.prev" ] && sysctl_user is-active --quiet steamvr.service; then
    # Keep only the restore step until SteamVR stops; it removes itself afterwards.
    R="$HOME/.local/state/steam-frame-tweaks/sft-dashboard-restore"
    install -m755 "$D/sft-dashboard" "$R"
    printf '[Service]\nExecStopPost=-%s restore\nExecStopPost=-/bin/rm -f %s %s\n' \
        "$R" "$U/steamvr.service.d/sft-dashboard.conf" "$R" > "$U/steamvr.service.d/sft-dashboard.conf"
    remove_files "$D" "$U/sft-vr-debugger.service" "$U/sft-dashboard.service"
else
    remove_files "$D" "$U/sft-vr-debugger.service" "$U/sft-dashboard.service" "$U/steamvr.service.d/sft-dashboard.conf"
fi
sysctl_user daemon-reload
