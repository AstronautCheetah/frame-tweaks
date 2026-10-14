#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
pkill -f "$HOME/.local/opt/claude-desktop/" 2>/dev/null || true
remove_files "$HOME/.local/opt/claude-desktop" "$BIN/claude-desktop" "$BIN/claude-desktop-update" "$APPS/com.anthropic.Claude.desktop" \
    "$LAUNCHER_ORIGINALS/com.anthropic.Claude.desktop"
find "$HOME/.local/share/icons/hicolor" -name "claude-desktop.*" -delete 2>/dev/null || true
