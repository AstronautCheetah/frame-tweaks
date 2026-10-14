#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
exec "$TWEAK_DIR/install.sh" --remove
