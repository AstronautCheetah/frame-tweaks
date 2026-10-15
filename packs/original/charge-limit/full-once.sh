#!/bin/bash
# Charge to 100% once (a button on its settings page): lifts the limit until the battery is full,
# or the Frame restarts; then the limit applies again.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/charge-limit" ] || die "$(t 'Install Battery charge limit first.')"
if [ "$("$BIN/charge-limit" --limit)" = off ]; then
    t 'The limit is off: the battery already charges to 100%.'; echo
    exit 0
fi
"$BIN/charge-limit" --full-once >/dev/null
t 'Charging to 100% once; then the limit applies again.'; echo
