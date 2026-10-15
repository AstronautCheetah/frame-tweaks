#!/bin/bash
# restart-plasmashell: bring back a crashed taskbar/system tray.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
install_i18n
install -m755 "$TWEAK_DIR/restart-plasmashell" "$BIN/"
say "$(t 'Installed %s' restart-plasmashell)"
