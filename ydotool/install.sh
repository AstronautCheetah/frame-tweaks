#!/bin/bash
# ydotool + user service: keystroke injection for any app (used by dictation/arrowpad).
source "$(dirname "$0")/../lib/common.sh"

[ -w /dev/uinput ] || die "/dev/uinput isn't writable. SteamOS normally grants it to the 'input' group: check 'groups'."

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
alarm_fetch extra ydotool "$T"
install -m755 "$T/usr/bin/ydotool" "$T/usr/bin/ydotoold" "$BIN/"

mkdir -p "$HOME/.config/systemd/user"
cp "$REPO_DIR/ydotool/ydotoold.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable --now ydotoold
sysctl_user is-active ydotoold >/dev/null && say "ydotoold running (socket /run/user/$(id -u)/.ydotool_socket)"
