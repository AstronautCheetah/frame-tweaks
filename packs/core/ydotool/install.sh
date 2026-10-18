#!/bin/bash
# ydotool + user service: keystroke injection for any app (used by dictation/arrowpad).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"

UINPUT=${FRAME_TWEAKS_UINPUT:-/dev/uinput}   # overridable for dev/test-tweaks.sh
[ -w "$UINPUT" ] || die "$(t "%s isn't writable. SteamOS normally grants it to the 'input' group: check 'groups'." "$UINPUT")"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
alarm_fetch extra ydotool "$T"
# Installed only if it runs here: both load (runs_here: what's missing, if not), and ydotool starts
# where it was unpacked (--help prints its commands and stops before looking for a daemon, here
# one whose socket isn't there; a time limit, for one that would wait anyway; ydotoold, the
# daemon, isn't started). Otherwise a working ydotool from before is kept.
if why=$(runs_here "$T/usr/bin/ydotool") && why=$(runs_here "$T/usr/bin/ydotoold") && why=$(t "ydotool didn't start") &&
   YDOTOOL_SOCKET="$T/no-daemon" timeout 10 "$T/usr/bin/ydotool" --help >/dev/null 2>&1; then
    install -m755 "$T/usr/bin/ydotool" "$T/usr/bin/ydotoold" "$BIN/"
elif [ -x "$BIN/ydotoold" ] && runs_here "$BIN/ydotoold" >/dev/null && runs_here "$BIN/ydotool" >/dev/null; then
    warn "$(t "Arch Linux ARM's current ydotool doesn't run on this SteamOS (%s); keeping the one you have." "$why")"
else
    die "$(t "Arch Linux ARM's current ydotool doesn't run on this SteamOS (%s)." "$why")"
fi

mkdir -p "$HOME/.config/systemd/user"
cp "$TWEAK_DIR/ydotoold.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable --now ydotoold
if sysctl_user is-active ydotoold >/dev/null; then
    say "$(t '%s running (socket %s)' ydotoold "/run/user/$(id -u)/.ydotool_socket")"
else
    warn "$(t "%s didn't start; see: %s" ydotoold "systemctl --user status ydotoold")"
fi
