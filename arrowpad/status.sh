#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/arrowpad" ] || status_missing "arrowpad not installed"
"$QT_VENV/bin/python" -c "import PyQt6" 2>/dev/null || status_warn "PyQt6 venv broken (re-run ./install.sh arrowpad)"
status_ok "arrowpad installed"
