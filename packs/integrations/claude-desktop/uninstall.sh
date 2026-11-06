#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# Closed, and gone before its files are: a ↻ Reinstall's install, run right after, found it still
# quitting, refused to close it, and left Claude Desktop uninstalled. (10 s, then for good.)
pkill -f "$HOME/.local/opt/claude-desktop/" 2>/dev/null || true
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    pgrep -f "$HOME/.local/opt/claude-desktop/" >/dev/null || break
    sleep 0.5
done
pkill -9 -f "$HOME/.local/opt/claude-desktop/" 2>/dev/null || true
remove_desktop com.anthropic.Claude.desktop
remove_files "$HOME/.local/opt/claude-desktop" "$BIN/claude-desktop" "$BIN/claude-desktop-update"
find "$HOME/.local/share/icons/hicolor" -name "claude-desktop.*" -delete 2>/dev/null || true
