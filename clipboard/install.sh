#!/bin/bash
# One clipboard for desktop mode and VR windows (dnut/clipboard-sync, built from upstream).
source "$(dirname "$0")/../lib/common.sh"
ROOT="$HOME/.local/share/frame-tweaks/clipboard-sync"
# Rust is needed only for this build: a pinned toolchain in a temporary folder (about 600 MB while
# it builds), deleted afterwards. (Homebrew's Rust, which older versions installed, takes 3.4 GB
# with its LLVM and stays installed.)
BUILD="$HOME/.cache/frame-tweaks/rust-build"
rm -rf "$BUILD" "$HOME/.local/share/frame-tweaks/cargo"          # (the latter: older versions' cache)
mkdir -p "$BUILD"
trap 'rm -rf "$BUILD"' EXIT
export RUSTUP_HOME="$BUILD/rustup" CARGO_HOME="$BUILD/cargo"
fetch_pinned clipboard "$BUILD/rustup-init" rust.pin
chmod +x "$BUILD/rustup-init"
say "Fetching Rust $(sed -n 's/^toolchain=//p' "$REPO_DIR/clipboard/rust.pin") (temporary, for the build)"
"$BUILD/rustup-init" -y -q --no-modify-path --profile minimal \
    --default-toolchain "$(sed -n 's/^toolchain=//p' "$REPO_DIR/clipboard/rust.pin")" ||
    die "couldn't set up Rust for the build"
export PATH="$CARGO_HOME/bin:$PATH"
if [ -x /home/linuxbrew/.linuxbrew/bin/rustc ]; then
    say "Homebrew's Rust (installed by older versions for this build) isn't needed any more; if you"
    say "don't use it yourself: brew uninstall rust && brew autoremove   (frees about 3.4 GB)"
fi
say "Building clipboard-sync from https://github.com/dnut/clipboard-sync (a few minutes)"
# The pinned commit, plus one small change (keep-images.patch): it only shares text, and used
# to replace a copied image with the last text a moment later.
SRC="$HOME/.local/share/frame-tweaks/src/clipboard-sync"
rev=$(sed -n 's/^rev=//p' "$REPO_DIR/clipboard/pin")
rm -rf "$SRC"
if git clone -q "$(sed -n 's/^url=//p' "$REPO_DIR/clipboard/pin")" "$SRC" &&
   git -C "$SRC" -c advice.detachedHead=false checkout -q "$rev"; then
    [ "$(git -C "$SRC" rev-parse HEAD)" = "$rev" ] || die "clipboard-sync: not the pinned commit"
else      # gone upstream: Frame Tweaks' copy of that commit's source (dev/mirror-pins.sh)
    warn "clipboard-sync's pinned commit isn't available upstream; using Frame Tweaks' copy"
    rm -rf "$SRC" && mkdir -p "$SRC"
    fetch_mirror "$(sed -n 's/^mirror=//p' "$REPO_DIR/clipboard/pin")" \
        "$(sed -n 's/^mirror_sha256=//p' "$REPO_DIR/clipboard/pin")" "$BUILD/src.tar.gz"
    tar -xzf "$BUILD/src.tar.gz" -C "$SRC" --strip-components=1
fi
git -C "$SRC" apply "$REPO_DIR/clipboard/keep-images.patch"
echo keep-images > "$SRC/.sft-patched"
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
