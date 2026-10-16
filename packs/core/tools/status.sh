#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/restart-plasmashell" ] || status_missing "$(t 'not installed')"
[ -x "$BIN/taskbar-guard" ] || status_warn "$(t 'installed without the taskbar watch (an older version): ↻ adds it')"
# In desktop mode, the watch should be running there.
if pgrep -u "$(id -u)" -x ksmserver >/dev/null && ! pgrep -u "$(id -u)" -f "^[^ ]*python3 $BIN/taskbar-guard\$" >/dev/null; then
    status_warn "$(t "installed; the taskbar watch isn't running in this desktop: ↻ starts it")"
fi
status_ok "$(t 'installed; watching the taskbar in desktop mode')"
