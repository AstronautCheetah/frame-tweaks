#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
CFG="$HOME/.var/app/org.signal.Signal/config/Signal/config.json"
flatpak info org.signal.Signal >/dev/null 2>&1 || status_missing "Signal (Flathub) not installed"
flatpak override --user --show org.signal.Signal 2>/dev/null | grep -q "SIGNAL_PASSWORD_STORE=kwallet6" || status_missing "Signal not set to use the wallet"
[ -f "$CFG" ] && grep -q "\"key\"" "$CFG" && status_warn "plaintext key still on disk (start Signal once more)"
grep -q signal-guard "$APPS/org.signal.Signal.desktop" 2>/dev/null && status_warn "uses the retired Signal guard (reinstall: ↻)"
grep -q wallet-gate "$APPS/org.signal.Signal.desktop" 2>/dev/null || status_warn "Signal opens without asking for the wallet password (Wallet apps: Password first)"
t=$("$BIN/app-timers" --list 2>/dev/null | awk '$1 == "org.signal.Signal" {print $2}')
status_ok "key in wallet; password first; $([ -n "$t" ] && echo "closes after $t min idle" || echo "no Close-after timer")"
