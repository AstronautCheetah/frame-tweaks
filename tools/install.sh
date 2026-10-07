#!/bin/bash
# restart-plasmashell: bring back a crashed taskbar/system tray.
source "$(dirname "$0")/../lib/common.sh"
ensure_path
install -m755 "$REPO_DIR/tools/restart-plasmashell" "$BIN/"
say "Installed restart-plasmashell"
