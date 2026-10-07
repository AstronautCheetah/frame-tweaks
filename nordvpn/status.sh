#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/nordvpn-wg" ] || status_missing "nordvpn-wg not installed"
[ -f "$HOME/.config/nordvpn-wg/private_key" ] || status_warn "not set up yet (run: nordvpn-wg setup)"
n=$(nmcli -t -f TYPE,NAME connection show | grep -c "^wireguard:NordVPN ")
st=$("$BIN/nordvpn-wg" status 2>/dev/null | sed -n 1p)
status_ok "$n location(s); ${st:-unknown}"
