---
title: Dictation
emoji: ⌨️
category: Accessibility
tier: core
summary: >-
  Speak instead of typing: one shortcut to record, then the text is typed and copied, all on the
  headset
what: >-
  Speech-to-text that runs on the headset itself, with whisper.cpp. Press a shortcut (or 🎤 on
  Arrow Pad's Tools layer) to start, press again to stop; the text is typed into the app you're
  using and copied to the clipboard.
why: >-
  Typing with controller lasers on a VR keyboard is slow. The Frame can transcribe speech
  locally, so you can talk instead, and your voice never leaves the headset.
author: "Frame Tweaks; engine: whisper.cpp (ggml-org), model: OpenAI Whisper"
source: {relation: uses, url: https://github.com/ggml-org/whisper.cpp}
depends: [ydotool]
icon: {file: frame-tweaks-dictate.png}
run: {label: Dictate}
config: [~/.config/frame-tweaks/dictate.conf]
changes: >-
  `~/.local/bin/dictate`, a **Dictate (toggle)** app-menu entry,
  `~/.config/frame-tweaks/dictate.conf`, the Whisper model in `~/.local/share/whisper`, a history
  of what you dictated (`~/.local/share/dictation-history.txt`, plain text); Homebrew's
  `whisper-cpp` and `wl-clipboard`
access: Microphone while recording; types through ydotool
survives_updates: Yes (everything is in your home folder and Homebrew)
undo: >-
  `./install.sh uninstall dictation` (keeps `~/.config/frame-tweaks/dictate.conf`, your
  dictation history and Homebrew's `whisper-cpp` and `wl-clipboard`)
test:
  offline: true
  keeps: [".config/frame-tweaks/dictate.conf"]
---
# Dictation

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Speech-to-text that runs on the headset itself, with whisper.cpp. Press a shortcut (or 🎤 on Arrow Pad's Tools layer) to start, press again to stop; the text is typed into the app you're using and copied to the clipboard.

**Why on a Steam Frame:** Typing with controller lasers on a VR keyboard is slow. The Frame can transcribe speech locally, so you can talk instead, and your voice never leaves the headset.
<!-- /generated:intro -->

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install dictation
```

It needs [Homebrew](../homebrew/) for whisper.cpp and the clipboard tool; if Homebrew isn't
there yet, the installer offers to set it up (it asks for your sudo password once). It also
downloads the Whisper model (a pinned file, checked against its SHA256) and sets up
[ydotool](../ydotool/), the helper it types through.

Then give it a button: bind **Dictate (toggle)** to a key in *System Settings → Keyboard →
Shortcuts*, and, if you like, that key to a controller button in Steam Input. Step by step:
[Dictate and Lock Wallet on a controller button](../../../docs/controller-shortcuts.md). With
[Arrow Pad](../arrowpad/) installed you already have one: **Tools**, then **🎤**.

## Use

1. Press your shortcut (or 🎤) once. A chime means it's recording. Speak.
2. Press it again. A second chime, then after a few seconds the text is
   - typed into the window you're using,
   - copied to the clipboard,
   - added to `~/.local/share/dictation-history.txt`, with the date and time.

A sentence that ends in `.`, `?` or `!` gets a space after it, so the next dictation carries
on naturally. The **▶ Dictate** button in the Frame Tweaks window does the same as the shortcut.

On Arrow Pad, the 🎤 key turns red while recording and yellow while transcribing.
`dictate --status` prints the same thing in a terminal: `idle`, `recording` or `transcribing`.

## Settings

Your settings live in `~/.config/frame-tweaks/dictate.conf` (created from
[`dictate.conf.example`](dictate.conf.example) on install). Remove the `#` in front of a line
to use it:

- `DICTATE_PROMPT`: words Whisper should spell your way, such as names or jargon.
- `DICTATE_LANG`: the language you speak, such as `de`, `fr` or `es` (default `en`), or `auto`
  to let Whisper guess.
- `DICTATE_MODEL`: the full path of a different whisper.cpp model, for example a smaller one
  for faster, less accurate text.
- `DICTATE_NOTYPE=1`: only copy the text, don't type it.
- `DICTATE_MAX_SECONDS`: stop a forgotten recording after this many seconds (default 300).

## How it works

- `pw-record` records the microphone (16 kHz, mono). whisper.cpp turns it into text with
  Whisper's multilingual `small` model. Nothing stays loaded between dictations: Whisper starts
  for each one and exits when it's done.
- Typing goes through [ydotool](../ydotool/), because KDE's Wayland desktop doesn't let ordinary
  programs send keys to other apps. Copying uses `wl-copy`, which the script points at the
  desktop's Wayland socket itself (shortcuts and launchers don't always say where it is).
- Whisper runs with `DISABLE_GAMESCOPE_WSI=1`, which keeps the Steam session's graphics layer
  out of its way.
- If the GPU build of whisper.cpp from groffta's
  [whisper-frame](https://github.com/groffta/whisper-frame) is already installed, Dictation uses
  it and shares its model file, instead of installing a second copy.

## Good to know

- **Taps are forgiving.** A second press within 0.7 s is ignored (a laser double-click). A
  press while a transcription is running is ignored too, with a "Still transcribing…" notice.
  Each recording has its own file, so a new one never overwrites one still being transcribed.
- **No phantom text.** Whisper tends to invent phrases for silence ("Thanks for watching",
  "Subs by …"). A recording whose loudest moment stays under −40 dB counts as "no speech", and
  those stock phrases are dropped when they're the whole result.
- **Something went wrong?** The log is `/run/user/$UID/dictate/dictate.log`, and the last
  recording is kept as `/run/user/$UID/dictate/last.wav` so you can listen to it. Both go away
  when the headset restarts.
- **Nothing typed, but the text was copied?** ydotool may need a restart: **▶ Restart** on the
  ydotool row in Frame Tweaks.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder and Homebrew)
- **Changes:** `~/.local/bin/dictate`, a **Dictate (toggle)** app-menu entry, `~/.config/frame-tweaks/dictate.conf`, the Whisper model in `~/.local/share/whisper`, a history of what you dictated (`~/.local/share/dictation-history.txt`, plain text); Homebrew's `whisper-cpp` and `wl-clipboard`
- **Unusual access:** Microphone while recording; types through ydotool
- **Undo:** `./install.sh uninstall dictation` (keeps `~/.config/frame-tweaks/dictate.conf`, your dictation history and Homebrew's `whisper-cpp` and `wl-clipboard`)
<!-- /generated:changes -->

## Credits

[whisper.cpp](https://github.com/ggml-org/whisper.cpp) (MIT) and OpenAI's
[Whisper](https://github.com/openai/whisper) models (MIT) do the transcription;
[ydotool](https://github.com/ReimuNotMoe/ydotool) (AGPL-3.0) types. Other dictation projects
for the Frame: [frame-voice](https://github.com/techieyann/frame-voice) and
[whisper-frame](https://github.com/groffta/whisper-frame). Its menu icon is the
[Noto Color Emoji](https://github.com/googlefonts/noto-emoji) font's 🎤 (SIL OFL 1.1) on a tile, drawn
by `dev/draw-icons.py` ([icons/README.md](../../../icons/README.md)). See also
[CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status dictation` · Remove: `./install.sh uninstall dictation`
