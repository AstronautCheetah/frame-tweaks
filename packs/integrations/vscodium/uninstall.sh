#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
flatpak uninstall -y --noninteractive com.vscodium.codium
say "$(t 'Kept your settings and extensions in ~/.var/app/com.vscodium.codium.')"
