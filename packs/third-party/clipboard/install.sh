#!/bin/bash
# One clipboard for desktop mode and VR windows (dnut/clipboard-sync, built from upstream).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
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
say "$(t 'Fetching Rust %s (temporary, for the build)' "$(sed -n 's/^toolchain=//p' "$TWEAK_DIR/rust.pin")")"
"$BUILD/rustup-init" -y -q --no-modify-path --profile minimal \
    --default-toolchain "$(sed -n 's/^toolchain=//p' "$TWEAK_DIR/rust.pin")" ||
    die "$(t "couldn't set up Rust for the build")"
export PATH="$CARGO_HOME/bin:$PATH"
if [ -x /home/linuxbrew/.linuxbrew/bin/rustc ]; then
    while IFS= read -r line; do say "$line"; done <<< "$(t "Homebrew's Rust (installed by older versions for this build) isn't needed any more; if you
don't use it yourself: %s   (frees about 3.4 GB)" "brew uninstall rust && brew autoremove")"
fi
say "$(t 'Building %s from %s (a few minutes)' clipboard-sync https://github.com/dnut/clipboard-sync)"
# The pinned commit, plus two changes (README.md, How it works). keep-images.patch: a copied
# image was replaced with the last text a moment later. sync-sessions.patch: the rest. A copy is
# shared, never written back where it came from, and the desktop's own Xwayland is left to KWin;
# files, pictures and the primary selection are shared too; a password keeps its mark and goes
# when its original goes; copies are counted as they happen (data-control, XFixes) instead of
# read five times a second; a start replaces nothing.
SRC="$HOME/.local/share/frame-tweaks/src/clipboard-sync"
rev=$(sed -n 's/^rev=//p' "$TWEAK_DIR/pin")
rm -rf "$SRC"
if git clone -q "$(sed -n 's/^url=//p' "$TWEAK_DIR/pin")" "$SRC" &&
   git -C "$SRC" -c advice.detachedHead=false checkout -q "$rev"; then
    [ "$(git -C "$SRC" rev-parse HEAD)" = "$rev" ] || die "$(t '%s: not the pinned commit' clipboard-sync)"
else      # gone upstream: Frame Tweaks' copy of that commit's source (dev/mirror-pins.sh)
    warn "$(t "%s's pinned commit isn't available upstream; using Frame Tweaks' copy" clipboard-sync)"
    rm -rf "$SRC" && mkdir -p "$SRC"
    fetch_mirror "$(sed -n 's/^mirror=//p' "$TWEAK_DIR/pin")" \
        "$(sed -n 's/^mirror_sha256=//p' "$TWEAK_DIR/pin")" "$BUILD/src.tar.gz"
    tar -xzf "$BUILD/src.tar.gz" -C "$SRC" --strip-components=1
fi
for p in keep-images sync-sessions; do git -C "$SRC" apply "$TWEAK_DIR/$p.patch"; done
echo keep-images sync-sessions > "$SRC/.sft-patched"         # (status.sh: an older build asks for a reinstall)
# (Its build files go in the temporary folder too: with --path, cargo keeps them in $SRC/target,
# about 350 MB that would stay.)
cargo install --locked --force --path "$SRC" --root "$ROOT" --target-dir "$BUILD/target"
install -m755 "$TWEAK_DIR/clipboard-sync-start" "$BIN/clipboard-sync-start"
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
    say "$(t '%s started' clipboard-sync)"
else
    say "$(t '%s starts with desktop mode.' clipboard-sync)"
fi
