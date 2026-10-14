#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# Older versions: Signal guard. (The wallet protections and timer stay: Wallet apps.)
sed -i "s| $BIN/signal-guard -- | |" "$APPS/org.signal.Signal.desktop" 2>/dev/null || true
pkill -f "^python3 $BIN/signal-guard( |$)" 2>/dev/null || true
remove_files "$BIN/signal-guard"
say "Signal keeps its wallet password and Close-after timer: change them in Wallet apps."
warn "The kwallet6 setting stays: Signal's database key now lives in the wallet, and switching back would lock you out."
