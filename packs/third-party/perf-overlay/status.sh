#!/bin/bash
# The link's status (lib/link.sh: installed, and which version), with one check of this tweak's
# own: the panel's service has to be enabled to start with SteamVR, and its installer's
# `systemctl --user enable` fails quietly in a desktop-mode terminal (no user bus there), which
# left the panel installed and never starting. And while SteamVR runs without it: closed from its
# dashboard (exit status 3, which its unit doesn't restart, though systemd files it as failed),
# not started yet (enabled after SteamVR started), or really failed.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNIT=frame-perf-overlay.service
rc=0; out=$(bash "$REPO_DIR/lib/link.sh" status perf-overlay) || rc=$?    # (common.sh: set -e)
if [ "$rc" -eq 0 ] && [ -f "$HOME/.config/systemd/user/$UNIT" ] &&
        [ "$(sysctl_user is-enabled "$UNIT" 2>/dev/null)" != enabled ]; then
    status_warn "$(t "installed, but not set to start with SteamVR (its installer's enable step fails from desktop mode): Show on its row sets it, or %s" "./install.sh run perf-overlay")"
fi
if [ "$rc" -eq 0 ] && [ -f "$HOME/.config/systemd/user/$UNIT" ]; then
    # (a copy outside the service, started from a menu entry while the service's was stopped: it holds
    # the panel's lock and shows nothing, and the service's copy waits behind it; Show ends it)
    main=$(sysctl_user show "$UNIT" -p MainPID --value 2>/dev/null) || main=0
    if [ -n "$(pgrep -f "^$HOME/.local/bin/frame-perf-overlay( |$)" 2>/dev/null | grep -vx "${main:-0}" || true)" ]; then
        status_warn "$(t 'a copy started from the menu is running outside its service and shows nothing: Show on its row ends it, so the service can show the panel')"
    fi
fi
if [ "$rc" -eq 0 ] && [ -f "$HOME/.config/systemd/user/$UNIT" ] && sysctl_user is-active --quiet steamvr.service &&
        ! sysctl_user is-active --quiet "$UNIT"; then
    code=$(sysctl_user show "$UNIT" -p ExecMainStatus --value 2>/dev/null) || code=""   # (common.sh: set -e)
    if [ "$code" = 3 ]; then
        status_ok "$(t 'installed; closed from its dashboard until the next SteamVR start (Show on its row starts it again)')"
    elif [ "$(sysctl_user is-active "$UNIT" 2>/dev/null)" = failed ]; then
        status_warn "$(t 'installed, but its service failed (exit status %s): Show on its row starts it again; its log: %s' \
                       "${code:-?}" "journalctl --user -u $UNIT")"
    fi
    status_ok "$(t 'installed; starts with the next SteamVR start (Show on its row starts it now)')"
fi
printf '%s\n' "$out"
exit "$rc"
