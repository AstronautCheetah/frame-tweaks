#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/nordvpn-wg" ] || status_missing "$(t '%s not installed' nordvpn-wg)"
[ -f "$HOME/.config/nordvpn-wg/private_key" ] || status_warn "$(t 'not set up yet (run: %s)' "nordvpn-wg setup")"
# Local only (no network call): status must be quick, the installer window runs it often.
all=$(nmcli -t -f TYPE,AUTOCONNECT,NAME connection show)
n=$(grep -c "^wireguard:[^:]*:NordVPN " <<<"$all" || true)   # (0 matches: grep exits 1)
start=$(sed -n 's/^wireguard:yes:NordVPN //p' <<<"$all" | head -1)    # (nordvpn-wg autoconnect)
up=$(nmcli -t -f TYPE,NAME connection show --active | sed -n 's/^wireguard:NordVPN //p' | head -1)
if [ -n "$start" ]; then
    [ -z "$up" ] || status_ok "$(t '%s location(s); connected via %s; connects at startup: %s' "$n" "$up" "$start")"
    status_ok "$(t '%s location(s); disconnected; connects at startup: %s' "$n" "$start")"
fi
[ -z "$up" ] || status_ok "$(t '%s location(s); connected via %s' "$n" "$up")"
status_ok "$(t '%s location(s); disconnected' "$n")"
