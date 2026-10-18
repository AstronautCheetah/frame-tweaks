#!/bin/bash
# Battery charge limit: charge-limit and its user service, and a udev rule (root's, so it asks for
# your sudo password once) that makes the charger's pause switch yours at each start.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
SWITCH=/sys/class/power_supply/pm8550b-charger/charging_pause
RULE=/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules
KEEP=/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf    # (SteamOS updates keep what it lists)

bash "$TWEAK_DIR/check-system.sh" >/dev/null || die "$(bash "$TWEAK_DIR/check-system.sh")"

rule=$(sed "s/@UID@/$(id -u)/" "$TWEAK_DIR/charge-limit.rules")
if [ "$(cat "$RULE" 2>/dev/null)" != "$rule" ] || [ "$(cat "$KEEP" 2>/dev/null)" != "$RULE" ] || [ ! -w "$SWITCH" ]; then
    printf '\n%s\n' "$(t "The charger's pause switch belongs to root. To make it yours, this asks for your sudo (admin)
password once, to add a udev rule (%s) that SteamOS updates keep." "$RULE")"
    if passwd -S "$USER" 2>/dev/null | grep -q " NP "; then
        die "$(t "Your user has no password, so sudo can't work. Set one with 'passwd', then re-run.")"
    fi
    # One sudo command for the rule, the list SteamOS updates keep and the switch, with -k: sudo
    # asks for the password and doesn't remember it, so nothing else running in this terminal,
    # meanwhile or after, can use it. (drop_sudo: in case.)
    added=1
    sudo -k sh -c 'printf "%s\n" "$1" > "$2" && printf "%s\n" "$2" > "$3" && chown "$4" "$5"' \
        sh "$rule" "$RULE" "$KEEP" "$(id -u)" "$SWITCH" || added=
    drop_sudo
    [ -n "$added" ] || die "$(t "Couldn't add the udev rule.")"
fi

install -m755 "$TWEAK_DIR/charge-limit" "$BIN/"
# Its watch on sleep (pauses charging near the limit before the Frame sleeps): D-Bus via jeepney.
ensure_tweaks_venv
install_py_tool "$TWEAK_DIR/charge-limit-sleep"
mkdir -p "$HOME/.config/systemd/user"
cp "$TWEAK_DIR/charge-limit.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable charge-limit
sysctl_user restart charge-limit
limit=$("$BIN/charge-limit" --limit)
if [ "$limit" = off ]; then
    say "$(t 'Installed; the limit is off (its settings), so the battery charges to 100%.')"
else
    say "$(t 'The battery now stops charging at %s%% while the Frame is on.' "$limit")"
fi
