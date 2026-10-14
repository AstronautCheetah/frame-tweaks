#!/bin/bash
source "$FRAME_TWEAKS_LIB/common.sh"
[ -x "$BIN/hello-frame" ] || status_missing "not installed"
[ -f "$APPS/hello-frame.desktop" ] || status_warn "its menu entry is missing (reinstall it)"
status_ok "in the app menu"
