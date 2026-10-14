#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
CFG="$HOME/.var/app/org.signal.Signal/config/Signal/config.json"
flatpak info org.signal.Signal >/dev/null 2>&1 || status_missing "$(t 'Signal (Flathub) not installed')"
flatpak override --user --show org.signal.Signal 2>/dev/null | grep -q "SIGNAL_PASSWORD_STORE=kwallet6" || status_missing "$(t 'Signal not set to use the wallet')"
[ -f "$CFG" ] && grep -q "\"key\"" "$CFG" && status_warn "$(t 'plaintext key still on disk (start Signal once more)')"
grep -q signal-guard "$APPS/org.signal.Signal.desktop" 2>/dev/null && status_warn "$(t 'uses the retired Signal guard (reinstall: ↻)')"
grep -q wallet-gate "$APPS/org.signal.Signal.desktop" 2>/dev/null || status_warn "$(t 'Signal opens without asking for the wallet password (Wallet apps: Password first)')"
mins=$("$BIN/app-timers" --list 2>/dev/null | awk '$1 == "org.signal.Signal" {print $2}')
[ -n "$mins" ] && status_ok "$(t 'key in wallet; password first; closes after %s min idle' "$mins")"
status_ok "$(t 'key in wallet; password first; no Close-after timer')"
