#!/bin/bash
# ▶ Charge to 100% once: lifts the limit until the battery is full (or the Frame restarts).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
"$BIN/charge-limit" --full-once >/dev/null
say "$(t 'Charging to 100% once; then the limit applies again.')"
