#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
exec "$BIN/dictate"     # toggles: run again to stop and type
