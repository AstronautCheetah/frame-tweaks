#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
CFG="$HOME/.var/app/org.signal.Signal/config/Signal/config.json"
flatpak info org.signal.Signal >/dev/null 2>&1 || status_missing "Signal (Flathub) not installed"
flatpak override --user --show org.signal.Signal 2>/dev/null | grep -q "SIGNAL_PASSWORD_STORE=kwallet6" || status_missing "Signal not set to use the wallet"
[ -f "$CFG" ] && grep -q "\"key\"" "$CFG" && status_warn "plaintext key still on disk (start Signal once more)"
grep -q signal-guard "$APPS/org.signal.Signal.desktop" 2>/dev/null || status_warn "idle guard missing from the Signal launcher"
status_ok "key in wallet; idle guard on ($(grep -oE "IDLE_MINUTES=[0-9.]+" "$HOME/.config/signal-guard.conf" 2>/dev/null || echo IDLE_MINUTES=15))"
