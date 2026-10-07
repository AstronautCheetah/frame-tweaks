#!/bin/bash
# One clipboard for desktop mode and VR windows (dnut/clipboard-sync, built from upstream).
source "$(dirname "$0")/../lib/common.sh"
need_brew
ROOT="$HOME/.local/share/frame-tweaks/clipboard-sync"
if ! command -v cargo >/dev/null; then
    say "Installing Rust (Homebrew) to build clipboard-sync"
    brew install rust
fi
say "Building clipboard-sync from https://github.com/dnut/clipboard-sync (a few minutes)"
CARGO_HOME="$HOME/.local/share/frame-tweaks/cargo" \
    cargo install --locked --force --git https://github.com/dnut/clipboard-sync --root "$ROOT"
ln -sf "$ROOT/bin/clipboard-sync" "$BIN/clipboard-sync"

# Start with the desktop session (KDE autostart): it must run with the nested desktop's
# environment to see both its Wayland clipboard and the VR session's X display.
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/clipboard-sync.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=clipboard-sync
Comment=One clipboard for desktop mode and VR windows (steam-frame-tweaks)
Exec=$BIN/clipboard-sync
X-KDE-autostart-phase=2
NoDisplay=true
DESKTOP

# Start it now if we're inside desktop mode.
if src=$(pgrep -u "$(id -u)" -x ksmserver | head -1) && [ -n "$src" ]; then
    pkill -u "$(id -u)" -x clipboard-sync 2>/dev/null || true
    mapfile -d '' envs < "/proc/$src/environ"
    (cd "$HOME" && env -i "${envs[@]}" setsid -f "$BIN/clipboard-sync" >/dev/null 2>&1 </dev/null)
    say "clipboard-sync started"
else
    say "clipboard-sync starts with desktop mode."
fi
