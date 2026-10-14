#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
b=$(command -v brew || { [ -x "$BREW" ] && echo "$BREW"; }) || status_missing "Homebrew not installed"
n=$("$b" list --formula -1 2>/dev/null | wc -l) || true
status_ok "$("$b" --version 2>/dev/null | sed -n 1p) ($n packages)"
