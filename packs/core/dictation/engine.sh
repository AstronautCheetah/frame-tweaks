#!/bin/bash
# Dictation's engine, as ⚙ Settings say (its Apply, and the install): Parakeet's venv and model
# downloaded when it's chosen; then the engine kept loaded, or stopped, as DICTATE_KEEP_LOADED says.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
CONF="$HOME/.config/frame-tweaks/dictate.conf"
setting() { sed -n "s/^[[:space:]]*$1=//p" "$CONF" 2>/dev/null | tr -d "\"'" | tail -1; }
P="$HOME/.local/share/frame-tweaks/parakeet"
if [ "$(setting DICTATE_ENGINE)" = parakeet ]; then
    if ! "$P/venv/bin/python" -c 'import onnx_asr, onnxruntime' 2>/dev/null; then
        say "$(t 'Setting up onnx-asr, the runtime Parakeet runs on')"
        echo "    $(t 'About 150 MB, in ~/.local/share/frame-tweaks/parakeet.')"
        new_venv "$P/venv" && pip_pinned "$P/venv" onnx-asr onnxruntime ||
            die "$(t "Parakeet's runtime couldn't be installed; Dictation goes on with Whisper")"
    fi
    # The model: each file checked against its pin (a file from an older pin, or cut short, is
    # downloaded again); .version says they all are, for this revision.
    ver=$(sed -n 's/^version=//p' "$TWEAK_DIR/parakeet-encoder.pin")
    if [ "$(cat "$P/model/.version" 2>/dev/null)" != "$ver" ]; then
        rm -f "$P/model/.version"; mkdir -p "$P/model"
        for part in config vocab decoder encoder; do
            pin="$TWEAK_DIR/parakeet-$part.pin"
            f="$P/model/$(basename "$(sed -n 's/^url=//p' "$pin")")"
            sha_ok "$(sed -n 's/^sha256=//p' "$pin")" "$f" && continue
            [ "$part" = encoder ] && say "$(t 'Downloading Parakeet (about 650 MB)')"
            fetch_pinned dictation "$f.part" "parakeet-$part.pin" && mv -f "$f.part" "$f"
        done
        echo "$ver" > "$P/model/.version"
    fi
    sed "1s|.*|#!$P/venv/bin/python|" "$TWEAK_DIR/dictate-parakeet" | write_file "$BIN/dictate-parakeet" 755
    say "$(t 'Dictation uses Parakeet.')"
elif [ -d "$P" ]; then
    say "$(t 'Dictation uses Whisper. Parakeet stays downloaded (~/.local/share/frame-tweaks/parakeet): uninstalling Dictation removes it.')"
fi
"$BIN/dictate" --apply
settings_applied
case $(setting DICTATE_KEEP_LOADED) in
    yes) say "$(t 'The engine stays loaded between dictations.')" ;;
esac
