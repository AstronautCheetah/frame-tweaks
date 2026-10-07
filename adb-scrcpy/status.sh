#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/adb" ] || status_missing "adb not installed"
"$BIN/adb" version >/dev/null 2>&1 || status_warn "adb installed but does not run (re-run ./install.sh adb-scrcpy)"
command -v scrcpy >/dev/null || [ -x /home/linuxbrew/.linuxbrew/bin/scrcpy ] || status_warn "scrcpy missing (brew install scrcpy)"
status_ok "adb $("$BIN/adb" version | sed -n "2s/Version //p"), scrcpy, phone launcher"
