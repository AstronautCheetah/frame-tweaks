#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
PATH="$BIN:${BREW%/brew}:$PATH"
command -v claude >/dev/null || status_missing "$(t 'Claude Code not installed')"
status_ok "$(t 'Claude Code %s (run: claude)' "$(claude --version 2>/dev/null | sed 's/ (Claude Code)//')")"
