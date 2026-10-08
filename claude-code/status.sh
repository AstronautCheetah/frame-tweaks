#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
PATH="$BIN:/home/linuxbrew/.linuxbrew/bin:$PATH"
command -v claude >/dev/null || status_missing "Claude Code not installed"
status_ok "Claude Code $(claude --version 2>/dev/null | sed 's/ (Claude Code)//') (run: claude)"
