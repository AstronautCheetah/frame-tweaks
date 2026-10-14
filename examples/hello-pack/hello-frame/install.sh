#!/bin/bash
# The installer runs this with the shared helpers' folder in $FRAME_TWEAKS_LIB.
source "$FRAME_TWEAKS_LIB/common.sh"
ensure_path
install -m755 "$TWEAK_DIR/hello-frame" "$BIN/hello-frame"
install_desktop "$TWEAK_DIR/hello-frame.desktop"
say "Open 'Hello Frame' from the app menu."
