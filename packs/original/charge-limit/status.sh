#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
SWITCH=${FRAME_TWEAKS_CHARGE_SWITCH:-/sys/class/power_supply/pm8550b-charger/charging_pause}
DEVICES=${FRAME_TWEAKS_STEAMOS_DEVICES:-/usr/share/steamos-manager/devices}
RUN=${FRAME_TWEAKS_CHARGE_RUN:-$XDG_RUNTIME_DIR_USER/charge-limit}
[ -f "$HOME/.config/systemd/user/charge-limit.service" ] || status_missing "$(t 'not installed')"
# Valve's own charge limit (Steam's Settings → Power on the Steam Deck) comes to the Frame once
# SteamOS's device file for it has a battery_charge_limit section: then this tweak should go.
for f in "$DEVICES"/*.toml; do
    grep -qs '^device = "steam_frame"' "$f" && grep -qs '^\[battery_charge_limit' "$f" &&
        status_warn "$(t "SteamOS now has its own charge limit (Steam → Settings → Power): use that, and uninstall this")"
done
[ -e "$SWITCH" ] || status_warn "$(t "This SteamOS has no charger pause switch, so the limit can't work")"
[ -w "$SWITCH" ] || status_warn "$(t "Can't pause charging: Reinstall it (it asks for your password)")"
sysctl_user is-active --quiet charge-limit || status_warn "$(t "Not running (Reinstall starts it)")"
bat=$("$BIN/charge-limit" --battery) || status_warn "$(t 'No battery found')"
cap=$(cat "$bat/capacity")
limit=$("$BIN/charge-limit" --limit)
[ -e "$RUN/full-once" ] && status_ok "$(t 'Charging to 100%% once (now %s%%), then stopping at %s%% again' "$cap" "$limit")"
[ "$limit" = off ] && status_ok "$(t 'Limit off: charges to 100%% (now %s%%)' "$cap")"
# Paused but still charging (over 100 mA into the battery): the charger didn't take the pause.
if [ "$(cat "$SWITCH")" = 1 ] && [ -e "$RUN/paused" ]; then
    [ "$(cat "$bat/current_now" 2>/dev/null || echo 0)" -gt 100000 ] &&
        status_warn "$(t "Paused at %s%%, but the battery still charges: the Frame's charger ignored the pause" "$cap")"
    status_ok "$(t 'Holding at %s%% (battery %s%%, not charging)' "$limit" "$cap")"
fi
# (the service checks as it starts, then every 30 seconds)
[ "$cap" -ge "$limit" ] &&
    status_warn "$(t "Battery at %s%%, but charging isn't paused; see: %s" "$cap" "journalctl --user -u charge-limit")"
status_ok "$(t 'Stops charging at %s%% (battery %s%%)' "$limit" "$cap")"
