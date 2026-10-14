#!/bin/bash
# ydotool + user service: keystroke injection for any app (used by dictation/arrowpad).
source "$(dirname "$0")/../lib/common.sh"

UINPUT=${FRAME_TWEAKS_UINPUT:-/dev/uinput}   # overridable for dev/test-tweaks.sh
[ -w "$UINPUT" ] || die "$UINPUT isn't writable. SteamOS normally grants it to the 'input' group: check 'groups'."

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
alarm_fetch extra ydotool "$T"
# Installed only if it runs here; otherwise a working ydotool from before is kept.
if missing=$(runs_here "$T/usr/bin/ydotool") && missing=$(runs_here "$T/usr/bin/ydotoold"); then
    install -m755 "$T/usr/bin/ydotool" "$T/usr/bin/ydotoold" "$BIN/"
elif [ -x "$BIN/ydotoold" ] && runs_here "$BIN/ydotoold" >/dev/null && runs_here "$BIN/ydotool" >/dev/null; then
    warn "Arch Linux ARM's current ydotool doesn't run on this SteamOS; keeping the one you have. Missing: $missing"
else
    die "Arch Linux ARM's current ydotool doesn't run on this SteamOS. Missing: $missing"
fi

mkdir -p "$HOME/.config/systemd/user"
cp "$REPO_DIR/ydotool/ydotoold.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable --now ydotoold
if sysctl_user is-active ydotoold >/dev/null; then
    say "ydotoold running (socket /run/user/$(id -u)/.ydotool_socket)"
else
    warn "ydotoold didn't start; see: systemctl --user status ydotoold"
fi
