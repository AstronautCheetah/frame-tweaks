#!/bin/bash
# Local Whisper speech-to-text: one shortcut to record, then text is typed + copied.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path

# Engine: whisper-frame's bundled GPU whisper-cli if installed, else Homebrew's whisper-cpp.
# wl-clipboard (copy to the clipboard) from Homebrew either way.
WF_CLI="$HOME/.local/lib/whisper-frame/whisper-cli"
if [ -x "$WF_CLI" ]; then
    say "$(t "Using whisper-frame's whisper-cli (no second copy)")"
    command -v wl-copy >/dev/null || { need_brew; brew install wl-clipboard; }
else
    need_brew
    say "$(t 'Installing whisper.cpp and wl-clipboard (Homebrew)')"
    brew install whisper-cpp wl-clipboard
fi

[ -x "$BIN/ydotoold" ] && [ -S "/run/user/$(id -u)/.ydotool_socket" ] ||
    "$(tweak_dir ydotool)/install.sh"

# Model: the same file whisper-frame uses, so installing both never keeps two copies.
MODELS="$HOME/.local/share/whisper"; MODEL=ggml-small-q8_0.bin
mkdir -p "$MODELS"
# Full Keyboard's on-device dictation uses the same file: a copy it has is shared, not downloaded
# again, and one this has is shared with it (lib/link-path/frame-tweaks-share-whisper).
"$REPO_DIR/lib/link-path/frame-tweaks-share-whisper"
if [ ! -f "$MODELS/$MODEL" ]; then
    say "$(t 'Downloading Whisper model %s' "$MODEL")"
    fetch_pinned dictation "$MODELS/$MODEL.part"     # pinned revision and SHA256 (dictation/pin)
    mv "$MODELS/$MODEL.part" "$MODELS/$MODEL"
    "$REPO_DIR/lib/link-path/frame-tweaks-share-whisper"
fi
# Silero voice activity detection (dictate: Whisper hears only the speech). Optional: if it can't be
# downloaded, Dictation works as before, without it.
VAD=$(basename "$(sed -n 's/^url=//p' "$TWEAK_DIR/vad.pin")")
if [ ! -f "$MODELS/$VAD" ]; then
    if ( fetch_pinned dictation "$MODELS/$VAD.part" vad.pin ); then mv "$MODELS/$VAD.part" "$MODELS/$VAD"
    else rm -f "$MODELS/$VAD.part"; warn "$(t 'No voice activity detection (its download failed): Whisper hears the whole recording.')"; fi
fi
# Models older versions downloaded; the shared one replaces them, unless a DICTATE_MODEL line in
# use names one. (Not one commented out: the example's, copied into every dictate.conf, names one.)
for old in ggml-small.en-q5_1.bin ggml-base.en-q5_1.bin; do
    if [ -f "$MODELS/$old" ] && ! grep -qsE "^[[:space:]]*DICTATE_MODEL=.*$old" "$HOME/.config/frame-tweaks/dictate.conf"; then
        rm -f "$MODELS/$old" && say "$(t 'Removed old model %s (replaced by the shared %s)' "$old" "$MODEL")"
    fi
done

install_i18n         # (dictate's notifications in your language)
install -m755 "$TWEAK_DIR/dictate" "$BIN/dictate"
install_icon frame-tweaks-dictate
install_desktop "$TWEAK_DIR/dictate.desktop"
mkdir -p "$HOME/.config/frame-tweaks"
[ -f "$HOME/.config/frame-tweaks/dictate.conf" ] || cp "$TWEAK_DIR/dictate.conf.example" "$HOME/.config/frame-tweaks/dictate.conf"
# Your dictation history is readable by you alone (older versions left it readable by everyone).
hist="$HOME/.local/share/dictation-history.txt"
[ ! -f "$hist" ] || chmod 600 "$hist"

# Hold Menu on the right controller to dictate, in VR (dictate-button, while SteamVR runs). It
# needs the openvr bindings, on SteamVR's own library (VR_LIB): without SteamVR it's left out,
# before anything is downloaded.
UNIT="$HOME/.config/systemd/user/frame-tweaks-dictate-button.service"
if [ -f "$VR_LIB" ] && ensure_tweaks_venv && ensure_openvr "$TWEAKS_VENV"; then
    install_py_tool "$TWEAK_DIR/dictate-button"
    write_file "$UNIT" <<UNITFILE
[Unit]
Description=Dictation on a controller button, while SteamVR runs (Frame Tweaks)
After=steamvr.service
PartOf=steamvr.service
# A crash loop gives up: 10 starts within 5 minutes and it stays stopped, rather than restart
# for ever; running steadily, old starts age out. (systemd's own limit, 5 in 10 s, would never
# trip with the growing waits below.)
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
ExecStart=$BIN/dictate-button
# On a crash only (not a clean exit, nor a stop by Frame Tweaks): again after 1 s, the wait
# doubling with each restart up to 32 s (systemd 254+; the Frame has 257).
Restart=on-failure
RestartSec=1
RestartSteps=5
RestartMaxDelaySec=32

[Install]
WantedBy=steamvr.service
UNITFILE
    sysctl_user daemon-reload || true
    sysctl_user enable frame-tweaks-dictate-button.service 2>/dev/null || true
    if sysctl_user is-active --quiet steamvr.service; then
        sysctl_user restart frame-tweaks-dictate-button.service || true
    fi
    # shellcheck source=button-names.sh
    source "$TWEAK_DIR/button-names.sh"
    if [ "$(dictate_button)" = off ]; then
        say "$(t 'No controller button for dictation: choose one in ⚙ Settings (./install.sh settings dictation).')"
    else
        say "$(t 'In VR, hold %s to start or stop dictating (another button: ⚙ Settings).' "$(button_name "$(dictate_button)")")"
    fi
else
    warn "$(t "No SteamVR here, so no controller button for dictation; the shortcut works as before.")"
fi

# The engine kept loaded between dictations, when ⚙ Settings say so (DICTATE_KEEP_LOADED=yes):
# dictate --serve, on the fast cores; the first thing stopped when memory runs out, so VR wins.
write_file "$HOME/.config/systemd/user/frame-tweaks-dictate-engine.service" <<UNITFILE
[Unit]
Description=Dictation's engine, kept loaded (Frame Tweaks)
# A crash loop gives up: 10 starts within 5 minutes and it stays stopped, rather than restart
# for ever; running steadily, old starts age out. (systemd's own limit, 5 in 10 s, would never
# trip with the growing waits below.)
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
ExecStart=$BIN/dictate --serve
OOMScoreAdjust=900
# On a crash only (not a clean exit, nor a stop by Frame Tweaks): again after 1 s, the wait
# doubling with each restart up to 32 s (systemd 254+; the Frame has 257).
Restart=on-failure
RestartSec=1
RestartSteps=5
RestartMaxDelaySec=32
UNITFILE
sysctl_user daemon-reload || true
"$TWEAK_DIR/engine.sh" || warn "$(t "Dictation's engine setting couldn't be applied; it uses Whisper")"

# Dictate (toggle) in the menus, as DICTATE_MENU says (by default hidden while a controller button
# toggles dictation: dictate-menu).
install -m755 "$TWEAK_DIR/dictate-menu" "$BIN/dictate-menu"
"$BIN/dictate-menu" >/dev/null || true

say "$(t "Done. Bind 'Dictate (toggle)' to a key too, if you like: %s" docs/controller-shortcuts.md)"
