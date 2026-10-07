#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
[ -x "$BIN/wallet-unlock" ] || status_missing "wallet tools not installed"
sysctl_user is-active --quiet wallet-lock-sync || status_warn "wallet-lock-sync not running: closing the wallet would not lock it (re-run ./install.sh wallet)"
n=$("$BIN/wallet-launcher" --list 2>/dev/null | wc -l)
state=$("$BIN/wallet-unlock" --status 2>/dev/null || echo unknown)
grep -q oauth_token "$HOME/.config/gh/hosts.yml" 2>/dev/null && status_warn "gh token stored in plain text (re-run ./install.sh wallet)"
status_ok "wallet $state; $n app launcher(s) routed/gated"
