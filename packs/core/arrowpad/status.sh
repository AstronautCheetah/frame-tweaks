#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/arrowpad" ] || status_missing "$(t 'arrowpad not installed')"
"$QT_VENV/bin/python" -c "import PyQt6" 2>/dev/null || status_warn "$(t 'PyQt6 venv broken (re-run ./install.sh arrowpad)')"
status_ok "$(t 'arrowpad installed')"
