#!/bin/bash
# whisper-frame (groffta): hold Select or a mic under any floating window to dictate.
source "$(dirname "$0")/../lib/common.sh"
API=https://api.github.com/repos/groffta/whisper-frame/releases/latest
TAG=$(curl -fsSL "$API" | sed -n 's/.*"tag_name": *"\(v[^"]*\)".*/\1/p' | head -1)
[ -n "$TAG" ] || die "couldn't find the latest whisper-frame release"
VER=${TAG#v}
if [ "$(cat "$HOME/.local/lib/whisper-frame/VERSION" 2>/dev/null)" = "$VER" ]; then
    say "whisper-frame $VER already installed"
else
    T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
    REL="https://github.com/groffta/whisper-frame/releases/download/$TAG"
    say "Downloading whisper-frame $VER"
    curl -fsSL -o "$T/SHA256SUMS" "$REL/SHA256SUMS"
    curl -fL# -o "$T/whisper-frame-$VER-aarch64.tar.gz" "$REL/whisper-frame-$VER-aarch64.tar.gz"
    (cd "$T" && sha256sum -c --ignore-missing --quiet SHA256SUMS) || die "checksum mismatch"
    tar -xzf "$T/whisper-frame-$VER-aarch64.tar.gz" -C "$T"
    # Its installer reuses ~/.local/share/whisper/ggml-small-q8_0.bin if present (shared
    # with our dictation), and needs the user systemd bus.
    (cd "$T/whisper-frame-$VER" && XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR_USER" \
        DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR_USER/bus" ./install.sh)
    echo "$VER" > "$HOME/.local/lib/whisper-frame/VERSION"
fi
# The window mic (whisper-panel) polls SteamVR's compositor for every window's position ~60
# times a second; measured here it costs ~31% of a core across whisper-panel, vrwebhelper and
# vrserver, enough for visible jitter. Off unless asked for.
if [ "${WHISPER_FRAME_WINDOW_MIC:-0}" = 1 ]; then
    mkdir -p "$HOME/.config/systemd/user/whisper-panel.service.d"
    cp "$REPO_DIR/whisper-frame/steamvr.conf" "$HOME/.config/systemd/user/whisper-panel.service.d/"
    sysctl_user daemon-reload
    sysctl_user reenable whisper-panel >/dev/null 2>&1 || true
    sysctl_user restart whisper-panel || true
    warn "Window mic on: it costs noticeable VR performance (see whisper-frame/README.md)."
else
    sysctl_user disable --now whisper-panel >/dev/null 2>&1 || true
    say "Window mic off (VR performance). Enable with: WHISPER_FRAME_WINDOW_MIC=1 ./install.sh whisper-frame"
fi
say "Hold the headset's Select button until the beep to dictate."
