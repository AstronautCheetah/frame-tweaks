#!/bin/bash
# Speech engine (helper): Piper (natural offline voice, used by Screen snip's Narrate) and the
# espeak-ng it ships with, wired into speech-dispatcher, so Orca (Screen reader) and other apps
# that speak through it have a voice. SteamOS has speech-dispatcher's espeak-ng module but not
# espeak-ng itself, so without this they're silent.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/speech"
mkdir -p "$D"
# Older versions kept Piper and the voice inside Screen snip: move them over.
OLD="$HOME/.local/share/frame-tweaks/snip"
[ -d "$OLD/piper" ] && [ ! -d "$D/piper" ] && mv "$OLD/piper" "$D/piper"
for f in voice.onnx voice.onnx.json voice.version; do
    [ -f "$OLD/$f" ] && [ ! -f "$D/$f" ] && mv "$OLD/$f" "$D/$f"
done

if [ ! -x "$D/piper/piper" ] || [ "$(cat "$D/piper/.version" 2>/dev/null)" != "$(pin_version speech)" ]; then
    say "Downloading Piper (speech)"
    t=$(mktemp -d)
    fetch_pinned speech "$t/piper.tgz"
    rm -rf "$D/piper" && tar -xzf "$t/piper.tgz" -C "$D" && rm -rf "$t"
    [ -x "$D/piper/piper" ] || die "the Piper download didn't contain piper/piper"
    pin_version speech > "$D/piper/.version"
fi
voice_rev=$(sed -n 's/^version=//p' "$TWEAK_DIR/voice.pin")
if [ "$(cat "$D/voice.version" 2>/dev/null)" != "$voice_rev" ]; then
    say "Downloading the voice (about 60 MB)"
    fetch_pinned speech "$D/voice.onnx.part" voice.pin && mv "$D/voice.onnx.part" "$D/voice.onnx"
    fetch_pinned speech "$D/voice.onnx.json.part" voice-config.pin && mv "$D/voice.onnx.json.part" "$D/voice.onnx.json"
    echo "$voice_rev" > "$D/voice.version"
fi

# speech-dispatcher: its espeak-ng module, run with Piper's espeak-ng library and voice data.
cat > "$D/sd_espeak-ng" <<WRAP
#!/bin/sh
# speech-dispatcher's espeak-ng module with the espeak-ng that comes with Piper (Frame Tweaks).
export LD_LIBRARY_PATH="$D/piper\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export ESPEAK_DATA_PATH="$D/piper"
exec /usr/lib/speech-dispatcher/speech-dispatcher-modules/sd_espeak-ng "\$@"
WRAP
chmod 755 "$D/sd_espeak-ng"
# A user speechd.conf replaces the system one: start from it, add the module, make it the default.
C="$HOME/.config/speech-dispatcher"
backup_file speech "$C/speechd.conf"
backup_file speech "$C/modules/espeak-ng.conf"
mkdir -p "$C/modules"
cp /etc/speech-dispatcher/modules/espeak-ng.conf "$C/modules/espeak-ng.conf"
# (its relative Include of clients/*.conf would look in ~/.config: point it at the system's)
{ grep -v -E '^\s*(AddModule|DefaultModule)\b' /etc/speech-dispatcher/speechd.conf |
      sed 's|^Include "clients/|Include "/etc/speech-dispatcher/clients/|' 
  echo "# Frame Tweaks (speech): espeak-ng from Piper's download"
  echo "AddModule \"espeak-ng\" \"$D/sd_espeak-ng\" \"espeak-ng.conf\""
  echo "DefaultModule espeak-ng"; } > "$C/speechd.conf"
# A running speech-dispatcher keeps its old (voiceless) setup: let the next client start it anew.
pkill -u "$(id -u)" -x speech-dispatcher 2>/dev/null || true
say "Speech ready: Orca and other speech-dispatcher apps use espeak-ng; Narrate uses Piper."
