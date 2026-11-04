#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNIT=frame-tweaks-tray-host.service
NAME=org.kde.StatusNotifierWatcher
PROC=${FRAME_TWEAKS_PROC:-/proc}     # (another, for the tests)
[ -x "$BIN/frame-tweaks-tray-host" ] && [ -f "$HOME/.config/systemd/user/$UNIT" ] || status_missing "$(t 'not installed')"
if ! sysctl_user is-active --quiet gamescope-session.target; then
    sysctl_user is-enabled --quiet "$UNIT" 2>/dev/null ||
        status_warn "$(t "won't start with the VR session: not enabled (↻ Reinstall enables it)")"
    ! sysctl_user is-failed --quiet "$UNIT" 2>/dev/null ||
        status_warn "$(t 'service failed (%s)' "journalctl --user -u $UNIT")"
    status_ok "$(t 'installed; starts with the VR session')"
fi
# The pid owning the watcher's name on the VR session's bus; nothing if no one owns it.
owner=$(busctl_user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus \
        GetConnectionUnixProcessID s "$NAME" 2>/dev/null | awk '{print $2}') || owner=
# Ours if the owner runs in our unit's cgroup: read at once with the owner, where the unit's
# MainPID, asked separately, could belong to a moment before or after.
if [ -n "$owner" ] && ! grep -qs "/$UNIT\$" "$PROC/$owner/cgroup"; then
    # (another program asked to replace it; ours waits in the queue and answers again once it's gone)
    status_ok "$(t 'another program answers tray icons in the VR session (%s)' "$(cat "$PROC/$owner/comm" 2>/dev/null || echo "pid $owner")")"
fi
sysctl_user is-active --quiet "$UNIT" || status_warn "$(t 'service not running (▶ Restart starts it)')"
[ -n "$owner" ] || status_warn "$(t "running, but not answering tray icons yet (%s)" "journalctl --user -u $UNIT")"
status_ok "$(t 'running: tray icons in the VR session get an answer')"
