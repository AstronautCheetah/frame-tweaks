#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
SWITCH=/sys/class/power_supply/pm8550b-charger/charging_pause
RULE=/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules
KEEP=/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf

# Stopping the service lets the battery charge again (and so does a pause of ours left behind).
sysctl_user disable --now charge-limit 2>/dev/null || true
paused="$XDG_RUNTIME_DIR_USER/charge-limit/paused"
if [ -e "$paused" ] && [ "$(cat "$SWITCH" 2>/dev/null)" = 1 ]; then
    printf '0\n' > "$SWITCH" 2>/dev/null || warn "$(t "Couldn't let the battery charge again: restart the Frame.")"
fi
remove_files "$BIN/charge-limit" "$BIN/charge-limit-sleep" "$HOME/.config/systemd/user/charge-limit.service" "${paused%/*}"
sysctl_user daemon-reload

if [ -e "$RULE" ] || [ -e "$KEEP" ]; then
    say "$(t 'Removing its udev rule needs your sudo (admin) password.')"
    if sudo -v && sudo rm -f "$RULE" "$KEEP"; then
        sudo chown root "$SWITCH" 2>/dev/null
        say "$(t 'removed %s' "$RULE")"
    else
        warn "$(t "Left its udev rule; it only lets you pause charging. Remove it with: %s" "sudo rm $RULE $KEEP")"
    fi
fi
