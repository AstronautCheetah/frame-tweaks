#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/clipboard-sync" ] || status_missing "clipboard-sync not installed"
pgrep -u "$(id -u)" -x clipboard-sync >/dev/null || status_warn "installed but not running (starts with desktop mode)"
n=$(pgrep -u "$(id -u)" -x clipboard-sync | wc -l)
[ "$n" -le 2 ] || status_warn "$n copies running (Restart fixes it)"   # (each forks one helper)
grep -q "keep-images" "$HOME/.local/share/frame-tweaks/src/clipboard-sync/.sft-patched" 2>/dev/null \
    || status_warn "older build: replaces copied images with text (Reinstall fixes it)"
status_ok "clipboard-sync running"
