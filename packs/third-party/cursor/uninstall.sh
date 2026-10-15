#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
remove_files "$HOME/.config/environment.d/90-kwin-software-cursor.conf"
say "$(t 'Takes effect after a reboot.')"
