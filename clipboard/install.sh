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
# The pinned commit, plus one small change (keep-images.patch): it only shares text, and used
# to replace a copied image with the last text a moment later.
SRC="$HOME/.local/share/frame-tweaks/src/clipboard-sync"
rev=$(sed -n 's/^rev=//p' "$REPO_DIR/clipboard/pin")
rm -rf "$SRC"
git clone -q "$(sed -n 's/^url=//p' "$REPO_DIR/clipboard/pin")" "$SRC"
git -C "$SRC" -c advice.detachedHead=false checkout -q "$rev"
[ "$(git -C "$SRC" rev-parse HEAD)" = "$rev" ] || die "clipboard-sync: not the pinned commit"
git -C "$SRC" apply "$REPO_DIR/clipboard/keep-images.patch"
echo keep-images > "$SRC/.sft-patched"
CARGO_HOME="$HOME/.local/share/frame-tweaks/cargo" \
    cargo install --locked --force --path "$SRC" --root "$ROOT"
install -m755 "$REPO_DIR/clipboard/clipboard-sync-start" "$BIN/clipboard-sync-start"
ln -sf "$ROOT/bin/clipboard-sync" "$BIN/clipboard-sync"

# Start with the desktop session (KDE autostart): it must run with the nested desktop's
# environment to see both its Wayland clipboard and the VR session's X display.
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/clipboard-sync.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=clipboard-sync
Comment=One clipboard for desktop mode and VR windows (Frame Tweaks)
Exec=$BIN/clipboard-sync-start
X-KDE-autostart-phase=2
NoDisplay=true
DESKTOP

# Start it now if we're inside desktop mode.
if src=$(pgrep -u "$(id -u)" -x ksmserver | head -1) && [ -n "$src" ]; then
    mapfile -d '' envs < "/proc/$src/environ"
    (cd "$HOME" && env -i "${envs[@]}" setsid -f "$BIN/clipboard-sync-start" >/dev/null 2>&1 </dev/null)
    say "clipboard-sync started"
else
    say "clipboard-sync starts with desktop mode."
fi
