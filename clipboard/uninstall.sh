#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
pkill -u "$(id -u)" -x clipboard-sync 2>/dev/null || true
remove_files "$BIN/clipboard-sync" "$HOME/.local/share/frame-tweaks/clipboard-sync" "$HOME/.config/autostart/clipboard-sync.desktop"
say "Kept Rust (brew uninstall rust) and the cargo cache (~/.local/share/frame-tweaks/cargo)."
