#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
exec konsole --separate -e bash -lc 'cd ~ && claude; exec bash'
