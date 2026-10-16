#!/bin/bash
# The icons are copied from the system's Breeze theme.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
for n in utilities-terminal preferences-system; do
    compgen -G "/usr/share/icons/breeze/apps/*/$n.svg" >/dev/null || { t 'Breeze no longer has %s' "$n"; echo; exit 1; }
done
t 'Breeze icons present'; echo
