#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
v=$(flatpak info com.vscodium.codium 2>/dev/null | sed -n 's/^ *Version: //p')
[ -n "$v" ] || status_missing "VSCodium not installed"
status_ok "VSCodium $v (Flathub)"
