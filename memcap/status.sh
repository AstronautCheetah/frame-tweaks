#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/capped" ] || status_missing "not installed"
grep -qw memory /sys/fs/cgroup/user.slice/user-"$(id -u)".slice/user@"$(id -u)".service/cgroup.controllers 2>/dev/null ||
    status_warn "systemd doesn't hand the memory controller to user services: caps can't apply"
CONF="$HOME/.config/frame-tweaks/memcap.conf"
status_ok "Whisper ≤ $(sed -n 's/^whisper_max=//p' "$CONF" | tail -1), scrcpy ≤ $(sed -n 's/^scrcpy_max=//p' "$CONF" | tail -1), VSCodium ≤ $(sed -n 's/^vscodium_max=//p' "$CONF" | tail -1)"
