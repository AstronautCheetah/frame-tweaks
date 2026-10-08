#!/bin/bash
# label: Open
source "$(dirname "$0")/../lib/common.sh"
exec konsole --separate -e bash -lc 'cd ~ && claude; exec bash'
