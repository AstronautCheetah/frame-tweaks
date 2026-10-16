#!/usr/bin/env bash
# For maintainers: which of the Frame's charger controls hold the battery still while plugged in?
# The research behind Battery charge limit (docs/research/battery-charge-limit.md): paused
# (charging_pause, what the tweak uses), the battery still gives part of the power; on SteamOS
# 0.5.6, charging_enable=0 and constant_charge_current 0-100 mA were ignored. Run it again after
# a SteamOS update to the charger (deckard-charger) or the kernel; a setting near 0 mA would let
# the tweak hold the limit without micro-cycles.
#   sudo bash dev/charge-hold-test.sh      (plugged in; about 4 minutes)
# It pauses and resumes charging and sets the charge current, and puts everything back as it was
# when it ends, or on Ctrl+C.
set -u
C=/sys/class/power_supply/pm8550b-charger
B=$(readlink -f /run/deckardcharger/BAT0)
[ "$(id -u)" = 0 ] || { echo "Run it with sudo."; exit 1; }
[ -w "$C/charging_enable" ] && [ -r "$B/current_now" ] || { echo "Charger or battery not found."; exit 1; }
pause=$(cat "$C/charging_pause") enable=$(cat "$C/charging_enable") cc=$(cat "$C/constant_charge_current")
restore() {
    echo "$cc" > "$C/constant_charge_current"; echo "$enable" > "$C/charging_enable"; echo "$pause" > "$C/charging_pause"
    echo "Put back: pause=$(cat "$C/charging_pause") enable=$(cat "$C/charging_enable") charge current=$(cat "$C/constant_charge_current")"
}
trap restore EXIT
trap 'exit 130' INT TERM
hold() {        # PAUSE ENABLE CURRENT, again each second (the tweak's service checks every 30 s)
    echo "$1" > "$C/charging_pause"; echo "$2" > "$C/charging_enable"
    echo "$3" > "$C/constant_charge_current" 2>/dev/null
    return 0
}
# sample LABEL RESTART PAUSE ENABLE CURRENT: hold the setting (after a 3 s pause first if RESTART
# is 1), let it settle, then the battery's current every 2 s for 20 s and the average
sample() {
    local label=$1 restart=$2 _ v sum=0 line=
    shift 2
    if [ "$restart" = 1 ]; then hold 1 "$2" "$3"; sleep 3; fi
    for _ in 1 2 3 4; do hold "$@"; sleep 1; done
    for _ in $(seq 10); do
        hold "$@"
        v=$(cat "$B/current_now"); sum=$((sum + v)); line+=" $((v / 1000))"
        sleep 2
    done
    printf '%-46s avg %5d mA:%s\n' "$label" $((sum / 10000)) "$line"
}
echo "Battery $(cat "$B/capacity")%. Battery current in mA: + charging, - giving power."
for restart in 0 1; do
    [ "$restart" = 1 ] && echo "-- the same, each after a 3 s pause and resume:"
    sample "paused (what the tweak does)" "$restart" 1 1 "$cc"
    sample "charging_enable=0" "$restart" 0 0 "$cc"
    for ua in 0 100000; do
        sample "charge current $((ua / 1000)) mA" "$restart" 0 1 "$ua"
    done
    sample "charging as normal" "$restart" 0 1 "$cc"
done
echo "charge current now reads $(cat "$C/constant_charge_current"); status_detailed:"
tr '\n' ' ' < "$C/status_detailed"; echo
