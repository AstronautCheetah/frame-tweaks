#!/bin/bash
# What the charge limit needs from SteamOS: the Frame charger's pause switch.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
if [ ! -e /sys/class/power_supply/pm8550b-charger/charging_pause ]; then
    t "SteamOS no longer has: %s" "$(t "the charger's pause switch")"; echo
    exit 1
fi
t "The charger's pause switch is there"; echo
