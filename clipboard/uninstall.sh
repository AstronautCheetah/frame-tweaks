#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
pkill -u "$(id -u)" -x clipboard-sync 2>/dev/null || true
remove_files "$BIN/clipboard-sync" "$BIN/clipboard-sync-start" "$HOME/.local/share/frame-tweaks/src/clipboard-sync" "$HOME/.local/share/frame-tweaks/clipboard-sync" "$HOME/.config/autostart/clipboard-sync.desktop"
remove_files "$HOME/.local/share/frame-tweaks/cargo" "$HOME/.cache/frame-tweaks/rust-build"   # (older versions' build cache)
if [ -x /home/linuxbrew/.linuxbrew/bin/rustc ]; then
    say "Homebrew's Rust (installed by older versions for this build) is still there; if you don't use it:"
    say "  brew uninstall rust && brew autoremove     (frees about 3.4 GB)"
fi
