#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
command -v plasmashell >/dev/null || { t '%s not found' plasmashell; echo; exit 1; }
t '%s present' plasmashell; echo
