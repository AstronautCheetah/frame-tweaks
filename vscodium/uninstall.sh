#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
flatpak uninstall -y --noninteractive com.vscodium.codium
say "Kept your settings and extensions in ~/.var/app/com.vscodium.codium."
