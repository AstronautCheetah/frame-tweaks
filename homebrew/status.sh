#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BREW" ] || status_missing "Homebrew not installed"
n=$("$BREW" list --formula -1 2>/dev/null | wc -l) || true
status_ok "$("$BREW" --version 2>/dev/null | sed -n 1p) ($n packages)"
