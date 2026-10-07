#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
sed -i "s| $BIN/signal-guard -- | |" "$APPS/org.signal.Signal.desktop" 2>/dev/null || true
remove_files "$BIN/signal-guard"
warn "The kwallet6 setting stays: Signal's database key now lives in the wallet, and switching back would lock you out."
