#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
v="$HOME/.local/opt/claude-desktop/.deb-version"
[ -f "$v" ] || status_missing "Claude Desktop not installed"
status_ok "Claude Desktop $(cat "$v") (update: claude-desktop-update)"
