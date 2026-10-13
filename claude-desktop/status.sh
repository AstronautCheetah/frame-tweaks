#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
v="$HOME/.local/opt/claude-desktop/.deb-version"
[ -f "$v" ] || status_missing "Claude Desktop not installed"
[ -L "$BIN/claude-desktop" ] &&
    status_warn "Claude Desktop starts without the KDE wallet, so sign-ins aren't kept: reinstall it"
# Since Claude last started: could it encrypt? If not, your sign-in won't survive a restart.
log="$HOME/.config/Claude/logs/main.log"
if [ -f "$log" ] && pgrep -f "^$HOME/.local/opt/claude-desktop/claude-desktop" >/dev/null &&
   awk '/\] Starting app \{/ {prev = s; s = NR}           # a second launch hands over and quits:
        /Not main instance/ {s = prev}                    # (not the running one)
        /isEncryptionAvailable=false/ {b = NR} END {exit !(b > s)}' "$log"; then
    status_warn "Claude Desktop can't reach the KDE wallet this time, so it won't keep your sign-in: quit it and open it again"
fi
status_ok "Claude Desktop $(cat "$v") (update: claude-desktop-update)"
