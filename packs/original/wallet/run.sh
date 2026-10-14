#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
if [ "$("$BIN/wallet-unlock" --status)" = unlocked ]; then
    notify-send -a Wallet "Wallet already unlocked" "Lock it now with the Lock Wallet menu entry."
else
    exec "$BIN/wallet-unlock"
fi
