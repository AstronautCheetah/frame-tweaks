#!/bin/bash
# KDE wallet pieces wallet-unlock and the broker talk to.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
miss=()
for b in kwalletd6 ksecretd kdialog; do command -v "$b" >/dev/null || miss+=("$b"); done
[ -S "/run/user/$(id -u)/bus" ] || miss+=("$(t 'Steam session D-Bus')")
[ ${#miss[@]} -eq 0 ] || { t 'missing: %s' "${miss[*]}"; echo; exit 1; }
t "kwalletd6, ksecretd, kdialog and the Steam session's D-Bus present"; echo
