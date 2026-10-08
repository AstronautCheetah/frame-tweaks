#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/nordvpn-wg" ] || status_missing "nordvpn-wg not installed"
[ -f "$HOME/.config/nordvpn-wg/private_key" ] || status_warn "not set up yet (run: nordvpn-wg setup)"
# Local only (no network call): status must be quick, the installer window runs it often.
n=$(nmcli -t -f TYPE,NAME connection show | grep -c "^wireguard:NordVPN ")
up=$(nmcli -t -f TYPE,NAME connection show --active | sed -n 's/^wireguard:NordVPN //p' | head -1)
if [ -n "$up" ]; then state="connected via $up"; else state="disconnected"; fi
status_ok "$n location(s); $state"
