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
if [ -x "$BIN/charge-limit-sleep" ] && ! pgrep -u "$(id -u)" -f "$BIN/charge-limit-sleep" >/dev/null; then
    status_warn "$(t "Not watching for sleep, so the battery can charge past the limit while the Frame is asleep (Reinstall fixes it)")"
fi
bat=$("$BIN/charge-limit" --battery) || status_warn "$(t 'No battery found')"
cap=$(cat "$bat/capacity")
limit=$("$BIN/charge-limit" --limit)
# (the limit off first: Charge to 100% once may be pending, with no limit to go back to)
[ "$limit" = off ] && status_ok "$(t 'Battery %s%%; the limit is off: it charges to 100%%' "$cap")"
[ -e "$RUN/full-once" ] && status_ok "$(t 'Battery %s%%; charging to 100%% once, then stopping at %s%% again' "$cap" "$limit")"
# Paused but still charging (over 100 mA into the battery): the charger didn't take the pause.
if [ "$(cat "$SWITCH")" = 1 ] && [ -e "$RUN/paused" ]; then
    [ "$(cat "$bat/current_now" 2>/dev/null || echo 0)" -gt 100000 ] &&
        status_warn "$(t "Paused at %s%%, but the battery still charges: the Frame's charger ignored the pause" "$cap")"
    # (well over it: charged while the Frame was asleep or off, or by Charge to 100% once)
    [ "$cap" -gt $((limit + 2)) ] &&
        status_ok "$(t "Battery %s%%; not charging until it's below %s%%" "$cap" "$limit")"
    status_ok "$(t 'Battery %s%%; holding at the %s%% limit, not charging' "$cap" "$limit")"
fi
# (the service checks as it starts, then every 30 seconds)
[ "$cap" -ge "$limit" ] &&
    status_warn "$(t "Battery at %s%%, but charging isn't paused; see: %s" "$cap" "journalctl --user -u charge-limit")"
status_ok "$(t 'Battery %s%%; charging stops at %s%%' "$cap" "$limit")"
