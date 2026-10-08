#!/bin/bash
# label: Dictate
source "$(dirname "$0")/../lib/common.sh"
exec "$BIN/dictate"     # toggles: run again to stop and type
