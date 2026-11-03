#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNITS="$HOME/.config/systemd/user"
DROPIN=frame-tweaks-vr-memory-guard.conf
CG=${FRAME_TWEAKS_CGROUP_USER:-/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service}
[ -f "$UNITS/app.slice.d/$DROPIN" ] || status_missing "$(t 'not installed')"
grep -qw memory "$CG/cgroup.controllers" 2>/dev/null ||
    status_warn "$(t "systemd doesn't hand the memory controller to your services here, so the limits can't apply")"
limit=$(cat "$CG/app.slice/memory.max" 2>/dev/null)
[ -n "$limit" ] && [ "$limit" != max ] ||
    status_warn "$(t "the apps' limit isn't in force yet: run the install again, or log out and back in")"
used=$(cat "$CG/app.slice/memory.current" 2>/dev/null || echo 0)
own=0
for f in "$UNITS"/app-flatpak-*-.scope.d/"$DROPIN"; do [ -f "$f" ] && own=$((own + 1)); done
status_ok "$(t 'Flatpak apps %s of %s MB (apps with a limit of their own: %s); SteamVR given priority' "$(( used / 1048576 ))" "$(( limit / 1048576 ))" "$own")"
