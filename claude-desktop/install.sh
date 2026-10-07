#!/bin/bash
# Claude Desktop (official Linux arm64 beta), unpacked into ~/.local/opt.
source "$(dirname "$0")/../lib/common.sh"
ensure_path
install -m755 "$REPO_DIR/claude-desktop/claude-desktop-update" "$BIN/claude-desktop-update"
"$BIN/claude-desktop-update"
say "Update later with: claude-desktop-update"
