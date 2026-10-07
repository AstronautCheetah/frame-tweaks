#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
remove_files "$HOME/.config/environment.d/90-kwin-software-cursor.conf"
say "Takes effect after a reboot."
