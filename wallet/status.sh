#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/wallet-unlock" ] || status_missing "wallet tools not installed"
sysctl_user is-active --quiet wallet-lock-sync || status_warn "wallet-lock-sync not running: closing the wallet would not lock it (re-run ./install.sh wallet)"
sysctl_user is-active --quiet app-timers || status_warn "app-timers not running: apps with a timer won't be closed (re-run ./install.sh wallet)"
n=$("$BIN/wallet-launcher" --list 2>/dev/null | wc -l)
state=$("$BIN/wallet-unlock" --status 2>/dev/null || echo unknown)
grep -q oauth_token "$HOME/.config/gh/hosts.yml" 2>/dev/null && status_warn "gh token stored in plain text (re-run ./install.sh wallet)"
if [ "$state" = unlocked ] && ! sysctl_user is-active --quiet wallet-autolock.timer; then
    status_warn "wallet unlocked with no auto-lock scheduled (run: wallet-unlock --schedule-lock)"
fi
status_ok "wallet $state; $n app launcher(s) routed/gated"
