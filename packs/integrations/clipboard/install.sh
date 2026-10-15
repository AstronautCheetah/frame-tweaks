#!/bin/bash
# One clipboard for desktop mode and VR windows: Frame Tweaks' build of clipboard-sync
# (AstronautCheetah/clipboard-sync: dnut/clipboard-sync with Frame Tweaks' changes), its pinned,
# checked aarch64 release.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ROOT="$HOME/.local/share/frame-tweaks/clipboard-sync"
VER=$(pin_version clipboard)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
say "$(t 'Downloading %s %s' clipboard-sync "$VER")"
fetch_pinned clipboard "$T/clipboard-sync.tar.gz"
tar -xzf "$T/clipboard-sync.tar.gz" -C "$T"
write_file "$ROOT/bin/clipboard-sync" 755 < "$T/clipboard-sync-$VER-aarch64-linux/clipboard-sync"
echo "$VER" > "$ROOT/VERSION"
# Older versions built it on the Frame: their source, build folders and Rust cache go.
rm -rf "$HOME/.local/share/frame-tweaks/src/clipboard-sync" "$HOME/.cache/frame-tweaks/rust-build" \
    "$HOME/.local/share/frame-tweaks/cargo"
if [ -x /home/linuxbrew/.linuxbrew/bin/rustc ]; then
    while IFS= read -r line; do say "$line"; done <<< "$(t "Homebrew's Rust (installed by older versions for this build) isn't needed any more; if you
don't use it yourself: %s   (frees about 3.4 GB)" "brew uninstall rust && brew autoremove")"
fi
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
