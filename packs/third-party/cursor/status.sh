#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
f="$HOME/.config/environment.d/90-kwin-software-cursor.conf"
# Does desktop mode's running session have the software cursor? A session reads environment.d as
# it starts, so it keeps the setting until it ends (desktop mode closed, or a reboot). (This
# check may run from the VR session, which never has it; KWin's own environment isn't readable,
# so ask Plasma's shell.)
shell=$(pgrep -u "$(id -u)" -x plasmashell | head -1 || true)
in_session() { [ -n "$shell" ] && tr '\0' '\n' < "/proc/$shell/environ" 2>/dev/null | grep -qx 'KWIN_FORCE_SW_CURSOR=1'; }
if [ ! -f "$f" ]; then
    # (removed by hand or by ./install.sh tidy: the session that has it keeps it)
    in_session && status_missing "$(t 'removed; desktop mode keeps its software pointer (a second, black X) until it restarts, or the next reboot')"
    status_missing "$(t 'cursor fix not installed')"
fi
why=$(bash "$(dirname "$0")/needed.sh") ||
    status_warn "$(t 'not needed any more, and it adds a second pointer (a black X): uninstall it. %s' "$why")"
if [ -n "$shell" ]; then
    in_session || status_warn "$(t 'installed; active after the next reboot')"
    status_ok "$(t 'software cursor active')"
fi
if [ "${KWIN_FORCE_SW_CURSOR:-}" = 1 ]; then status_ok "$(t 'software cursor active')"; fi
status_ok "$(t 'installed (active in desktop mode after a reboot)')"
