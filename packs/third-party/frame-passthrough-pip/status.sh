#!/bin/bash
# The link's status (lib/link.sh: installed, which version, a SteamVR restart owed), with one
# check of this tweak's own: its service has to be enabled to start with SteamVR, and its
# installer's `systemctl --user enable` fails quietly in a desktop-mode terminal (no user bus
# there). While SteamVR runs without it: not started yet, or failed.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
UNIT=framepip.service
rc=0; out=$(bash "$REPO_DIR/lib/link.sh" status frame-passthrough-pip) || rc=$?    # (common.sh: set -e)
if [ "$rc" -eq 0 ] && [ -f "$HOME/.config/systemd/user/$UNIT" ] &&
        [ "$(sysctl_user is-enabled "$UNIT" 2>/dev/null)" != enabled ]; then
    status_warn "$(t "installed, but not set to start with SteamVR (its installer's enable step fails from desktop mode): Open on its row sets it, or %s" "./install.sh run frame-passthrough-pip")"
fi
if [ "$rc" -eq 0 ] && [ -f "$HOME/.config/systemd/user/$UNIT" ] && sysctl_user is-active --quiet steamvr.service &&
        ! sysctl_user is-active --quiet "$UNIT"; then
    if [ "$(sysctl_user is-active "$UNIT" 2>/dev/null)" = failed ]; then
        code=$(sysctl_user show "$UNIT" -p ExecMainStatus --value 2>/dev/null) || code=""   # (common.sh: set -e)
        status_warn "$(t 'installed, but its service failed (exit status %s): Open on its row starts it again; its log: %s' \
                       "${code:-?}" "journalctl --user -u $UNIT")"
    fi
    status_ok "$(t 'installed; starts with the next SteamVR start (Open on its row starts it now)')"
fi
printf '%s\n' "$out"
exit "$rc"
