#!/bin/bash
# Claude Desktop (official Linux build, arm64), unpacked into ~/.local/opt.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
install -m755 "$TWEAK_DIR/claude-desktop-update" "$BIN/claude-desktop-update"
"$BIN/claude-desktop-update"
say "Update later with: claude-desktop-update"
