# Dictation: local Whisper speech-to-text

Speech-to-text that runs entirely on the Frame: whisper.cpp on the GPU (Vulkan).
The `small.en` model transcribes ~11 s of speech in ~3.5 s. Nothing leaves the device.

```sh
./install.sh dictation
```

## Use
1. Bind **Dictate (toggle)** to a key in *System Settings → Keyboard → Shortcuts*
   (and, if you like, map a controller button to that key in Steam Input).
2. Press once: a chime means it's recording. Speak.
3. Press again: a second chime, then within a few seconds the text is
   - typed into the focused window,
   - copied to the clipboard (appears in Klipper's history),
   - appended to `~/.local/share/dictation-history.txt`.

Sentences ending in `.`/`?`/`!` get a trailing space so dictations chain naturally.
Memory: nothing stays resident; whisper loads per transcription (~70 MB RAM +
~200 MB GPU for a few seconds). The `ydotoold` helper uses ~1.5 MB.

**Taps are forgiving:** a second tap within 0.7 s is ignored (laser double-clicks), taps
while a transcription is running are ignored with a "Still transcribing…" notice, and a
forgotten recording stops itself after 5 minutes. Each recording uses its own file, so a new
one can never overwrite one still being transcribed. `dictate --status` prints
`idle` / `recording` / `transcribing`; the Arrow Pad's 🎤 shows them as normal / red / yellow.

**No phantom text:** Whisper invents phrases for silence ("Thanks for watching", "Subs by …").
Recordings whose peak stays under −40 dB count as "no speech", and those stock phrases are
dropped when they're the whole result.

## Configure: `~/.config/dictate.conf`
See [`dictate.conf.example`](dictate.conf.example):
- `DICTATE_PROMPT`: words Whisper should spell your way (names, jargon).
- `DICTATE_MODEL`: e.g. `ggml-base.en-q5_1.bin` for faster, less accurate output.
- `DICTATE_NOTYPE=1`: clipboard only, no typing.
- `DICTATE_MAX_SECONDS=300`: auto-stop a recording after this long.

## Troubleshooting
Log: `/run/user/$UID/dictate/dictate.log`. Last recording: `/run/user/$UID/dictate/last.wav`.

## How it works / gotchas
- Recording: `pw-record` at 16 kHz mono. Typing: `ydotool` (kernel uinput) because
  KDE Wayland doesn't let ordinary apps inject keys.
- Desktop mode runs **nested**. Plasma's Wayland socket is under
  `/run/user/$UID/nested_plasma/`, but apps started from shortcuts see
  `XDG_RUNTIME_DIR=/run/user/$UID`, so `wl-copy` silently failed. The script finds the socket itself.
- whisper.cpp's Vulkan backend crashes in the Gamescope WSI layer, so it runs with `DISABLE_GAMESCOPE_WSI=1`.

---
Check: `./install.sh status dictation` · Remove: `./install.sh uninstall dictation`
