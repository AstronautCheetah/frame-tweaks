#!/bin/bash
# Speech engine (helper): Piper (natural offline voice, used by Screen snip's Narrate) and the
# espeak-ng it ships with, wired into speech-dispatcher where SteamOS has it, so Orca (Screen
# reader) and other apps that speak through it have a voice. SteamOS before 0.5.6 had
# speech-dispatcher's espeak-ng module but not espeak-ng itself; 0.5.6 removed speech-dispatcher.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/speech"
SDROOT=${FRAME_TWEAKS_SPEECHD_ROOT:-}
SD_ETC="$SDROOT/etc/speech-dispatcher"
SD_MODULE="$SDROOT/usr/lib/speech-dispatcher/speech-dispatcher-modules/sd_espeak-ng"
mkdir -p "$D"
# Older versions kept Piper and the voice inside Screen snip: move them over.
OLD="$HOME/.local/share/frame-tweaks/snip"
[ -d "$OLD/piper" ] && [ ! -d "$D/piper" ] && mv "$OLD/piper" "$D/piper"
for f in voice.onnx voice.onnx.json voice.version; do
    [ -f "$OLD/$f" ] && [ ! -f "$D/$f" ] && mv "$OLD/$f" "$D/$f"
done

if [ ! -x "$D/piper/piper" ] || [ "$(cat "$D/piper/.version" 2>/dev/null)" != "$(pin_version speech)" ]; then
    say "$(t 'Downloading Piper (speech)')"
    t=$(mktemp -d)
    fetch_pinned speech "$t/piper.tgz"
    rm -rf "$D/piper" && tar -xzf "$t/piper.tgz" -C "$D" && rm -rf "$t"
    [ -x "$D/piper/piper" ] || die "$(t "the Piper download didn't contain %s" piper/piper)"
    pin_version speech > "$D/piper/.version"
fi
chmod +x "$D/piper/espeak-ng" 2>/dev/null || true      # (Piper's archive ships it without the x bit)

# The settings (Frame Tweaks window → ⚙ Settings, or ./install.sh settings speech): which engine
# Narrate uses and which language. voices.tsv lists the languages (dev/speech-voices.py).
CONF="$HOME/.config/frame-tweaks/speech.conf"
lang=en_US engine=piper
[ -f "$CONF" ] && { lang=$(sed -n 's/^SPEECH_LANGUAGE=//p' "$CONF" | tr -d "\"'" | tail -1); engine=$(sed -n 's/^SPEECH_ENGINE=//p' "$CONF" | tr -d "\"'" | tail -1); }
lang=${lang:-en_US}      # (a file without it, e.g. only the engine chosen, or reset: the default)
row=$(awk -F'\t' -v l="$lang" '$1 == l' "$TWEAK_DIR/voices.tsv")
[ -n "$row" ] || { warn "$(t "speech: unknown language '%s'; using English (US)" "$lang")"; lang=en_US; row=$(awk -F'\t' '$1 == "en_US"' "$TWEAK_DIR/voices.tsv"); }
IFS=$'\t' read -r _ label voice_file voice_sha json_sha espeak_voice <<< "$row"
voice_rev=$(sed -n 's/^version=//p' "$TWEAK_DIR/voice.pin")
# English (US) is voice.pin's (with Frame Tweaks' copy if Hugging Face lost it); the others come
# from the same revision of rhasspy/piper-voices, checked against voices.tsv's SHA256s.
want="$voice_rev"; [ "$lang" = en_US ] || want="$voice_rev:$voice_file"
if [ "$(cat "$D/voice.version" 2>/dev/null)" != "$want" ]; then
    say "$(t 'Downloading the %s voice (about 60 MB)' "$label")"
    if [ "$lang" = en_US ]; then
        fetch_pinned speech "$D/voice.onnx.part" voice.pin
        fetch_pinned speech "$D/voice.onnx.json.part" voice-config.pin
    else
        base="https://huggingface.co/rhasspy/piper-voices/resolve/$voice_rev/$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$voice_file")"
        { curl -fL# -o "$D/voice.onnx.part" "$base" && sha_ok "$voice_sha" "$D/voice.onnx.part"; } ||
            die "$(t "the %s voice didn't download, or isn't the expected file; nothing changed" "$label")"
        { curl -fsSL -o "$D/voice.onnx.json.part" "$base.json" && sha_ok "$json_sha" "$D/voice.onnx.json.part"; } ||
            die "$(t "the %s voice's settings didn't download, or aren't the expected file; nothing changed" "$label")"
    fi
    mv "$D/voice.onnx.part" "$D/voice.onnx" && mv "$D/voice.onnx.json.part" "$D/voice.onnx.json"
    echo "$want" > "$D/voice.version"
fi
# For Narrate's ⚙ panel (frame-snip): the languages, and a command that applies changed settings
# (this installer again, from wherever Frame Tweaks is).
cp "$TWEAK_DIR/voices.tsv" "$D/voices.tsv"
write_file "$D/apply" 755 <<APPLY
#!/bin/sh
# Applies the Speech engine settings (~/.config/frame-tweaks/speech.conf): Frame Tweaks' speech/install.sh.
exec env FRAME_TWEAKS_LIB="$FRAME_TWEAKS_LIB" bash "$TWEAK_DIR/install.sh"
APPLY
# What Narrate reads (frame-snip): the engine, and eSpeak NG's voice for this language.
printf 'engine=%s\nespeak_voice=%s\nlanguage=%s\n' "${engine:-piper}" "$espeak_voice" "$lang" > "$D/narrate.conf"

narrator=$([ "$engine" = espeak-ng ] && echo "eSpeak NG" || echo Piper)
C="$HOME/.config/speech-dispatcher"
if [ ! -x "$SD_MODULE" ] || [ ! -f "$SD_ETC/speechd.conf" ] || [ ! -f "$SD_ETC/modules/espeak-ng.conf" ]; then
    # No speech-dispatcher on this SteamOS: take out a setup made while it had one.
    restore_file speech "$C/speechd.conf"
    restore_file speech "$C/modules/espeak-ng.conf"
    rmdir "$C/modules" "$C" 2>/dev/null || true
    rm -f "$D/sd_espeak-ng"
    say "$(t 'Speech ready (%s): Narrate uses %s.' "$label" "$narrator")"
    exit 0
fi
# speech-dispatcher: its espeak-ng module, run with Piper's espeak-ng library and voice data.
write_file "$D/sd_espeak-ng" 755 <<WRAP
#!/bin/sh
# speech-dispatcher's espeak-ng module with the espeak-ng that comes with Piper (Frame Tweaks).
export LD_LIBRARY_PATH="$D/piper\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export ESPEAK_DATA_PATH="$D/piper"
exec "$SD_MODULE" "\$@"
WRAP
# A user speechd.conf replaces the system one: start from it, add the module, make it the default.
backup_file speech "$C/speechd.conf"
backup_file speech "$C/modules/espeak-ng.conf"
mkdir -p "$C/modules"
cp "$SD_ETC/modules/espeak-ng.conf" "$C/modules/espeak-ng.conf"
# (its relative Include of clients/*.conf would look in ~/.config: point it at the system's)
{ grep -v -E '^\s*(AddModule|DefaultModule)\b' "$SD_ETC/speechd.conf" |
      sed "s|^Include \"clients/|Include \"$SD_ETC/clients/|"
  echo "# Frame Tweaks (speech): espeak-ng from Piper's download"
  echo "AddModule \"espeak-ng\" \"$D/sd_espeak-ng\" \"espeak-ng.conf\""
  echo "DefaultModule espeak-ng"
  echo "DefaultLanguage \"${lang%%_*}\""; } > "$C/speechd.conf"
# A running speech-dispatcher keeps its old (voiceless) setup: let the next client start it anew.
pkill -u "$(id -u)" -x speech-dispatcher 2>/dev/null || true
say "$(t 'Speech ready (%s): Narrate uses %s; speech-dispatcher apps use eSpeak NG.' "$label" "$narrator")"
