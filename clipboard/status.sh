#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/clipboard-sync" ] || status_missing "clipboard-sync not installed"
pgrep -u "$(id -u)" -x clipboard-sync >/dev/null || status_warn "installed but not running (starts with desktop mode)"
status_ok "clipboard-sync running"
