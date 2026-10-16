#!/bin/bash
source "$FRAME_TWEAKS_LIB/common.sh"
remove_files "$BIN/hello-frame"
remove_desktop hello-frame.desktop
say "Kept your greeting: ~/.config/frame-tweaks/hello-frame.conf"
