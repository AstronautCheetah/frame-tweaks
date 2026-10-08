#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ "$(kreadconfig6 --file kaccessrc --group ScreenReader --key Enabled 2>/dev/null)" = true ] ||
    status_missing "screen reader off"
command -v orca >/dev/null || status_warn "enabled, but Orca isn't installed"
status_ok "Orca $(orca --version 2>/dev/null | grep -oE '[0-9.]+' | head -1) starts with desktop mode (Meta+Alt+S toggles)"
