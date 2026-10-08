#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/menu-icons"
[ -x "$D/menu-icons" ] && "$D/menu-icons" remove
remove_files "$D"
