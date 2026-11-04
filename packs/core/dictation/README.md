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
sudo: homebrew
source: {relation: uses, url: https://github.com/ggml-org/whisper.cpp}
depends: [ydotool]
icon: {file: frame-tweaks-dictate.png}
run: {label: Dictate}
config: [~/.config/frame-tweaks/dictate.conf]
changes: >-
  `~/.local/bin/dictate` and `dictate-menu`, a **Dictate (toggle)** app-menu entry (hidden while
  a controller button is set, unless you choose otherwise), with SteamVR
  `~/.local/bin/dictate-button` and its user service (`frame-tweaks-dictate-button.service`),
  `~/.config/frame-tweaks/dictate.conf`, the Whisper model and Silero's voice activity
  detection model in `~/.local/share/whisper` (the Whisper model shared with Full Keyboard's
  on-device dictation as a hard link, when that's installed: one copy on disk) (and, if you choose Parakeet, its model and runtime in
  `~/.local/share/frame-tweaks/parakeet`), the engine's user service
  (`frame-tweaks-dictate-engine.service`, running only if you keep it loaded), a history
  of what you dictated (`~/.local/share/dictation-history.txt`, plain text); Homebrew's
  `whisper-cpp` and `wl-clipboard`
access: >-
  Microphone while recording; types through ydotool; while SteamVR runs, watches the button you
  picked (a controller's, or the headset's Aux key through Linux); an engine kept loaded listens
  on 127.0.0.1 (this machine only)
survives_updates: Yes (everything is in your home folder and Homebrew)
undo: >-
  `./install.sh uninstall dictation` (keeps `~/.config/frame-tweaks/dictate.conf`, your
  dictation history and Homebrew's `whisper-cpp` and `wl-clipboard`)
settings:
  file: ~/.config/frame-tweaks/dictate.conf
  format: shell
  about: >-
    The engine turns your speech into text, on the Frame. In VR, hold the controller button to
    start dictating, and hold it again to stop; a short press does nothing here. The app in front
    still gets every press too, so the buttons are grouped by what else they do: the recommended
    ones do nothing else on a long hold, the others do (the laser's clicks, Home and Back over
    windows, the dashboard). If a game reacts to your hold, pick another.
  note: >-
    Applies within a second (in VR; otherwise at your next dictation). Choosing Parakeet: press
    Apply to download it (about 800 MB).
  options:
    - key: DICTATE_ENGINE
      title: Engine
      default: whisper
      choices:
        - {label: "Whisper (the default): 99 languages, uses your word list", value: whisper}
        - {label: "Parakeet: 25 European languages, fastest when kept loaded (press Apply)", value: parakeet}
    - key: DICTATE_KEEP_LOADED
      title: Keep the engine loaded
      default: "no"
      choices:
        - {label: "No (the default): loaded for each dictation, no memory used in between", value: "no"}
        - {label: "Yes: text sooner; memory in use all the time (Whisper 600 MB, Parakeet 1.3 GB)", value: "yes"}
    - key: DICTATE_VAD
      title: Whisper voice activity detection
      default: "yes"
      only_with: {DICTATE_ENGINE: whisper}
      choices:
        - {label: "On (the default): Whisper hears only the speech in your recording", value: "yes"}
        - {label: "Off: Whisper hears the whole recording", value: "no"}
    - key: DICTATE_TYPING
      title: Put the text in by
      default: type
      choices:
        - {label: "Typing it (the default); pasting what your keyboard layout can't type", value: type}
        - {label: "Always pasting it", value: paste}
    - key: DICTATE_MENU
      title: "Dictate (toggle) in the + menu"
      default: auto
      choices:
        - {label: "Automatic: hidden while a controller button is set", value: auto}
        - {label: Always shown, value: "yes"}
        - {label: Never shown, value: "no"}
    - key: DICTATE_BUTTON
      title: Controller button
      default: menu
      choices:
        - {label: "Recommended: Menu, right controller (the default)", value: menu}
        - {label: "Recommended: Y, right controller", value: "y"}
        - {label: "Recommended: Off", value: "off"}
        - {label: "Alternative: View, left controller", value: view}
        - {label: "Alternative: D-pad up, left controller", value: dpad_up}
        - {label: "Not recommended: A, right controller (the laser's Home over windows)", value: a}
        - {label: "Not recommended: B, right controller (the laser's Back over windows)", value: b}
        - {label: "Not recommended: X, right controller (the laser's middle click)", value: x}
        - {label: "Not recommended: D-pad down, left controller (the laser's Home)", value: dpad_down}
        - {label: "Not recommended: D-pad left, left controller (the laser's Back)", value: dpad_left}
        - {label: "Not recommended: D-pad right, left controller (the laser's middle click)", value: dpad_right}
        - {label: "Not recommended: left bumper (a laser click)", value: bumper_left}
        - {label: "Not recommended: right bumper (a laser click)", value: bumper_right}
        - {label: "Not recommended: left trigger (a laser click; games use it)", value: trigger_left}
        - {label: "Not recommended: right trigger (a laser click; games use it)", value: trigger_right}
        - {label: "Not recommended: left grip (picks up windows, switches the laser's hand)", value: grip_left}
        - {label: "Not recommended: right grip (picks up windows, switches the laser's hand)", value: grip_right}
        - {label: "Not recommended: left stick click (the laser's right click)", value: stick_left}
        - {label: "Not recommended: right stick click (the laser's right click)", value: stick_right}
        - {label: "Not recommended: Aux, on the headset (the dashboard; a held mouse button on the desktop)", value: aux}
    - key: DICTATE_BUTTON_HOLD
      title: Hold it for
      default: "0.6"
      choices:
        - {label: "0.4 seconds", value: "0.4"}
        - {label: "0.6 seconds (the default)", value: "0.6"}
        - {label: "1 second", value: "1"}
        - {label: "1.5 seconds", value: "1.5"}
  actions:
    - label: Apply
      script: engine.sh
      keys: [DICTATE_ENGINE, DICTATE_KEEP_LOADED]
      about: Downloads Parakeet if it's chosen, and loads or stops the engine as chosen.
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

In VR it has a button already: **hold Menu on the right controller** (about half a second) to
start dictating, and hold it again to stop. You can also bind **Dictate (toggle)** to a key in
*System Settings → Keyboard → Shortcuts* ([step by step](../../../docs/controller-shortcuts.md)),
and with [Arrow Pad](../arrowpad/) installed there's **Tools**, then **🎤**.

## Use

1. Hold **Menu** on the right controller until it ticks (or press your shortcut, or 🎤). A chime
   means it's recording. Speak.
2. Hold Menu again (or press the shortcut). A second chime, then after a few seconds the text is
   - typed into the window you're using,
   - copied to the clipboard,
   - added to `~/.local/share/dictation-history.txt`, with the date and time (only you can
     read it).

A sentence that ends in `.`, `?` or `!` gets a space after it, so the next dictation carries
on naturally. The **▶ Dictate** button in the Frame Tweaks window does the same as the shortcut.

Before typing, Dictation lets go of any Ctrl, Alt, Super or Shift still held down on the virtual
keyboard (latched or locked on Arrow Pad, say), so the text doesn't turn into shortcuts.

On Arrow Pad, the 🎤 key turns red while recording and yellow while transcribing.
`dictate --status` prints the same thing in a terminal: `idle`, `recording` or `transcribing`.

## Settings

Your settings live in `~/.config/frame-tweaks/dictate.conf` (created from
[`dictate.conf.example`](dictate.conf.example) on install). Remove the `#` in front of a line
to use it:

- `DICTATE_ENGINE`: `whisper` (the default) or `parakeet`; see [Engines](#engines). Choosing
  Parakeet in **⚙ Settings**, then **Apply**, downloads it.
- `DICTATE_KEEP_LOADED`: `no` (the default) or `yes`: the engine stays loaded between
  dictations, so the text comes sooner, but its memory stays in use (Whisper about 600 MB,
  Parakeet about 1.3 GB, out of the 16 GB VR shares).
- `DICTATE_VAD`: `yes` (the default) or `no`: Silero's voice activity detection hands Whisper
  only the stretches of your recording with speech, so pauses and room noise don't turn into
  invented words (four seconds of noise gave "you" without it, nothing with it). It doesn't
  listen: it reads the recording after you stop, and the mic is open only while you dictate.
  Parakeet doesn't use it.
- `DICTATE_TYPING`: `type` (the default) types the text, and pastes it when your keyboard
  layout has no key for one of its characters; `paste` always pastes it.
- `DICTATE_PROMPT`: words Whisper should spell your way, such as names or jargon.
- `DICTATE_LANG`: the language you speak, such as `de`, `fr` or `es` (default `en`), or `auto`
  to let Whisper guess.
- `DICTATE_MODEL`: the full path of a different whisper.cpp model, for example a smaller one
  for faster, less accurate text.
- `DICTATE_BEAM`: `1` (the default: greedy, fastest) or `5` (whisper.cpp's own beam search,
  about 1.5 times as slow on the Frame; it made no difference to the text in our trials).
- `DICTATE_NOTYPE=1`: only copy the text, don't type it.
- `DICTATE_MAX_SECONDS`: stop a forgotten recording after this many seconds (default 300).
- `DICTATE_MENU`: whether **Dictate (toggle)** is in Steam's VR "+" menu and the desktop's app
  menu: `auto` (the default: hidden while a controller button is set, shown when it's `off`),
  `yes` or `no`.
- `DICTATE_BUTTON`: the button you hold to dictate, or `off`. Every button reaches the app in
  front too (Dictation can watch a button but not take it), so the choices are grouped by what
  else that press does:

  | | Buttons | Why |
  |---|---|---|
  | **Recommended** | `menu` (right; the default), `y` (right), `off` | Nothing else on the Frame uses a long hold of them: SteamVR's laser and the desktop leave them alone, and most games act on a short press. |
  | **Alternatives** | `view` (left), `dpad_up` (left) | Also free from the laser and the desktop, but on the left hand, and games use them more. |
  | **Not recommended** | `a`, `b`, `x`, `dpad_down`, `dpad_left`, `dpad_right`, `bumper_left`, `bumper_right`, `trigger_left`, `trigger_right`, `grip_left`, `grip_right`, `stick_left`, `stick_right`, `aux` | Each already does something while you hold it: the laser's clicks, Home and Back over windows, picking up windows, or (`aux`, the headset's button) the dashboard and, on the desktop, a held mouse button. |

  The system buttons aren't offered: SteamVR keeps them for the dashboard, recentering and
  screenshots.
- `DICTATE_BUTTON_HOLD`: how long to hold it, in seconds (default 0.6). Changes to these two
  apply within a second, without reinstalling. They're also in **⚙ Settings** on Dictation's row
  in the Frame Tweaks window, and in `./install.sh settings dictation`.

## Engines

| | Whisper (the default) | Parakeet |
|---|---|---|
| Languages | 99; you say which (`DICTATE_LANG`) | 25 European ones, told apart by itself |
| Your word list (`DICTATE_PROMPT`) | Yes | No |
| A 10-second sentence, loaded for it | about 1.2 s | about 3 s (loading is most of it) |
| The same, kept loaded | 1 to 1.2 s | about 0.4 s |
| Memory while kept loaded | about 600 MB | about 1.3 GB |
| Download | 250 MB (installed with Dictation) | about 800 MB (when you choose it) |

Times measured on a Frame. Whisper is OpenAI's `small` model through whisper.cpp; Parakeet is
NVIDIA's Parakeet TDT 0.6B v3, int8, through onnx-asr. Both run on the Frame's CPU, offline.
Parakeet is the one to keep loaded; started for each dictation, Whisper is faster.

## How it works

- `pw-record` records the microphone (16 kHz, mono), and a quarter of a second more after you
  stop, so a stop pressed on the last word doesn't cut it off. Quiet speech is raised to a
  normal level first. Then the engine turns it into text, started for this one dictation, or,
  with `DICTATE_KEEP_LOADED=yes`, the one kept loaded
  (`frame-tweaks-dictate-engine.service`, the first thing stopped if memory runs out).
- Whisper runs on the Frame's six fast cores, decoding greedily, and works through only as
  much of its 30-second window as the recording needs: a 3-second clip takes about 0.6 s
  instead of 1.6. Silero's voice activity detection hands it only the stretches with speech
  (`DICTATE_VAD=no` turns that off).
- Typing goes through [ydotool](../ydotool/), because KDE's Wayland desktop doesn't let ordinary
  programs send keys to other apps. Copying uses `wl-copy`, which the script points at the
  desktop's Wayland socket itself (shortcuts and launchers don't always say where it is).
- ydotool types as on a US keyboard. With another keyboard layout in KDE (French, German,
  Latin American…), each character is typed with the key that types it on that layout, with
  Shift or AltGr, or a dead key first (´ then e for é), as you'd type it. Text with a
  character your layout has no key for (é on a US keyboard, 漢字 on any) is pasted instead:
  it goes into the clipboard and the selection, then Shift+Insert, which pastes in terminals
  as well as other apps. Pasting reaches the desktop's apps (in desktop mode, and its windows
  in VR), not a game's own window.
- **The controller button** is `dictate-button`, a small service that runs while SteamVR does
  (`frame-tweaks-dictate-button.service`, started and stopped with `steamvr.service`). On the
  Frame, SteamVR hands button presses only to the app in front, so it reads the button from its
  part in the controller's 3D model, which shows it pressed whatever has focus (the way Arrow
  Pad and Full Keyboard read the grips). It can watch the button but not take it: a long hold
  of Menu still reaches the game or window too, as a long Menu press. Without SteamVR, install
  leaves it out.
- Whisper runs with `DISABLE_GAMESCOPE_WSI=1`, which keeps the Steam session's graphics layer
  out of its way, and, for a GPU build, the Frame's Vulkan driver named.
- If the GPU build of whisper.cpp from groffta's
  [whisper-frame](https://github.com/groffta/whisper-frame) is already installed, Dictation uses
  it and shares its model file, instead of installing a second copy.

## Good to know

- **Taps are forgiving.** A second press within 0.7 s is ignored (a laser double-click). A
  press while a transcription is running is ignored too, with a "Still transcribing…" notice.
  Each recording has its own file, so a new one never overwrites one still being transcribed.
  If a recording stops early by itself (the microphone gone, say), what it caught is
  transcribed then, within half a second, and your next press starts a new recording.
- **No phantom text.** Whisper tends to invent phrases for silence ("Thanks for watching",
  "Subs by …"). A recording whose loudest moment stays under −40 dB counts as "no speech", and
  those stock phrases are dropped when they're the whole result. Voice activity detection also
  keeps pauses and room noise from Whisper.
- **Something went wrong?** The log is `/run/user/$UID/dictate/dictate.log`, and the last
  recording is kept as `/run/user/$UID/dictate/last.wav` so you can listen to it; the last one
  the engine heard nothing in, also as `last-no-text.wav`. They go away when the headset restarts, and like the history, only you can read them.
- **The game sees Menu too.** Most games open their menu on a short press; if one reacts to
  the long hold, set `DICTATE_BUTTON=y` (or `off`) in your settings.
- **Full Keyboard has a dictation of its own** (its mic key, from 0.11): both can be installed;
  use one at a time.
- **Nothing typed, but the text was copied?** ydotool may need a restart: **▶ Restart** on the
  ydotool row in Frame Tweaks.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder and Homebrew)
- **Changes:** `~/.local/bin/dictate` and `dictate-menu`, a **Dictate (toggle)** app-menu entry (hidden while a controller button is set, unless you choose otherwise), with SteamVR `~/.local/bin/dictate-button` and its user service (`frame-tweaks-dictate-button.service`), `~/.config/frame-tweaks/dictate.conf`, the Whisper model and Silero's voice activity detection model in `~/.local/share/whisper` (the Whisper model shared with Full Keyboard's on-device dictation as a hard link, when that's installed: one copy on disk) (and, if you choose Parakeet, its model and runtime in `~/.local/share/frame-tweaks/parakeet`), the engine's user service (`frame-tweaks-dictate-engine.service`, running only if you keep it loaded), a history of what you dictated (`~/.local/share/dictation-history.txt`, plain text); Homebrew's `whisper-cpp` and `wl-clipboard`
- **Unusual access:** Microphone while recording; types through ydotool; while SteamVR runs, watches the button you picked (a controller's, or the headset's Aux key through Linux); an engine kept loaded listens on 127.0.0.1 (this machine only)
- **Undo:** `./install.sh uninstall dictation` (keeps `~/.config/frame-tweaks/dictate.conf`, your dictation history and Homebrew's `whisper-cpp` and `wl-clipboard`)
<!-- /generated:changes -->

## Credits

[whisper.cpp](https://github.com/ggml-org/whisper.cpp) (MIT) and OpenAI's
[Whisper](https://github.com/openai/whisper) models (MIT) do the transcription;
[ydotool](https://github.com/ReimuNotMoe/ydotool) (AGPL-3.0) types. The Parakeet engine is
NVIDIA's [Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
(CC-BY-4.0), in istupakov's [ONNX export](https://huggingface.co/istupakov/parakeet-tdt-0.6b-v3-onnx),
run by [onnx-asr](https://github.com/istupakov/onnx-asr) (MIT) on
[ONNX Runtime](https://github.com/microsoft/onnxruntime) (MIT). Voice activity detection is
[Silero VAD](https://github.com/snakers4/silero-vad) (MIT), in whisper.cpp's
[conversion](https://huggingface.co/ggml-org/whisper-vad). The faster Whisper settings follow
[whisper-frame](https://github.com/groffta/whisper-frame)'s, and keeping Parakeet loaded follows
[mswietlicki/steam-frame-dictation](https://github.com/mswietlicki/steam-frame-dictation)'s
measurements. Other dictation projects
for the Frame: [frame-voice](https://github.com/techieyann/frame-voice) and
[whisper-frame](https://github.com/groffta/whisper-frame). Its menu icon is the
[Noto Color Emoji](https://github.com/googlefonts/noto-emoji) font's 🎤 (SIL OFL 1.1) on a tile, drawn
by `dev/draw-icons.py` ([icons/README.md](../../../icons/README.md)). See also
[CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status dictation` · Remove: `./install.sh uninstall dictation`
