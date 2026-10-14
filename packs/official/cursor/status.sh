#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
f="$HOME/.config/environment.d/90-kwin-software-cursor.conf"
[ -f "$f" ] || status_missing "cursor fix not installed"
# Is it active where it matters, in desktop mode's session? (This check may run from the VR
# session, which never has it; KWin's own environment isn't readable, so ask Plasma's shell.)
shell=$(pgrep -u "$(id -u)" -x plasmashell | head -1)
if [ -n "$shell" ]; then
    tr '\0' '\n' < "/proc/$shell/environ" 2>/dev/null | grep -qx 'KWIN_FORCE_SW_CURSOR=1' ||
        status_warn "installed; active after the next reboot"
    status_ok "software cursor active"
fi
[ "${KWIN_FORCE_SW_CURSOR:-}" = 1 ] && status_ok "software cursor active"
status_ok "installed (active in desktop mode after a reboot)"
