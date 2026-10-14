#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/wallet-unlock" ] || status_missing "$(t 'wallet tools not installed')"
sysctl_user is-active --quiet wallet-lock-sync || status_warn "$(t '%s not running: closing the wallet would not lock it (re-run %s)' wallet-lock-sync "./install.sh wallet")"
sysctl_user is-active --quiet app-timers || status_warn "$(t "%s not running: apps with a timer won't be closed (re-run %s)" app-timers "./install.sh wallet")"
n=$("$BIN/wallet-launcher" --list 2>/dev/null | wc -l)
state=$("$BIN/wallet-unlock" --status 2>/dev/null || echo unknown)
grep -q oauth_token "$HOME/.config/gh/hosts.yml" 2>/dev/null && status_warn "$(t 'gh token stored in plain text (re-run %s)' "./install.sh wallet")"
if [ "$state" = unlocked ] && ! sysctl_user is-active --quiet wallet-autolock.timer; then
    status_warn "$(t 'wallet unlocked with no auto-lock scheduled (run: %s)' "wallet-unlock --schedule-lock")"
fi
case $state in
    locked) status_ok "$(t 'wallet locked; %s app launcher(s) routed/gated' "$n")" ;;
    unlocked) status_ok "$(t 'wallet unlocked; %s app launcher(s) routed/gated' "$n")" ;;
esac
status_ok "$(t 'wallet %s; %s app launcher(s) routed/gated' "$state" "$n")"
