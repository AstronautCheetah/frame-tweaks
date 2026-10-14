---
title: whisper-frame
emoji: 🎙️
category: Accessibility
tier: core
summary: >-
  groffta's dictation: hold Select or a mic under any floating window (shares dictation's model)
what: >-
  groffta's dictation: hold the headset's Select button, or the mic under any floating window.
  Installed from upstream; shares dictation's model.
why: >-
  Dictate without menus or the desktop, straight into the window you're looking at in VR.
author: groffta (whisper-frame); SteamVR-restart fix by Frame Tweaks
source: {relation: from, url: https://github.com/groffta/whisper-frame}
hidden_by_default: true
icon: {theme: audio-input-microphone}
known_issue:
  version: "0.2.0"
  short: ⚠ v0.2.0 has performance issues in VR (window mic)
  long: >-
    Version 0.2.0 has performance issues: its window mic polls the compositor about 60 times a
    second, using ~31% of a CPU core and making VR judder. That's why this row is hidden by
    default and the window mic is installed switched off.
  latest: https://api.github.com/repos/groffta/whisper-frame/releases/latest
changes: >-
  Upstream's own installer (user services `whisper-ptt`, `whisper-panel`), pinned release
access: Microphone; listens for the headset's Select button
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall whisper-frame`"
upstream_readme: https://raw.githubusercontent.com/groffta/whisper-frame/v0.2.0/README.md
---
# whisper-frame: dictate into any window

[groffta/whisper-frame](https://github.com/groffta/whisper-frame) adds two ways to dictate,
typed into the focused window:

<!-- generated:glance (dev/gen-docs.py, from each tweak's README front matter) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** Upstream's own installer (user services `whisper-ptt`, `whisper-panel`), pinned release
> - **Unusual access:** Microphone; listens for the headset's Select button
> - **Undo:** `./install.sh uninstall whisper-frame`
<!-- /generated:glance -->

- **Hold the headset's Select button** until the beep, speak, release.
- **Hold the mic under any floating window** (it appears at each window's bottom-right).

```sh
./install.sh install whisper-frame
```

**The window mic is off by default.** It tracks every floating window by polling SteamVR's
compositor about 60 times a second; measured on a Frame that costs about 31% of a CPU core
(whisper-panel itself plus extra work in vrwebhelper and vrserver), which showed up as jitter
when turning the head. Turn it on with `WHISPER_FRAME_WINDOW_MIC=1 ./install.sh install whisper-frame`.
The Select-button dictation costs nothing while idle.

This installs whisper-frame's **latest upstream release** (checksum-verified, with its own
installer), so updates come from upstream; re-run to update. Two additions:
- **Shared model:** whisper-frame and our [dictation](../dictation/) use the same
  `~/.local/share/whisper/ggml-small-q8_0.bin`, and dictation uses whisper-frame's bundled
  whisper-cli when it's there, so there are no duplicate copies.
- **SteamVR restarts:** if you enable the window mic, a systemd drop-in restarts it together with
  SteamVR (it loses its connection and doesn't recover on its own).

## Credits
whisper-frame is groffta's (MIT); it bundles whisper.cpp (MIT). See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status whisper-frame` · Remove: `./install.sh uninstall whisper-frame`

<!-- generated:upstream (dev/gen-docs.py, from upstream.md) -->
---

*The rest of this page is [groffta/whisper-frame](https://github.com/groffta/whisper-frame)'s own README at `v0.2.0`, as its author wrote it (only links and heading levels adjusted), included for its instructions and credits. Everything above is Frame Tweaks'.*

## whisper-frame

Push-to-talk dictation for the Steam Frame. Whisper Small runs on the headset, on the Adreno 750, and types into the window gamescope already has focused.

This is a user-local install. SteamOS keeps the root filesystem read-only, and files under your home directory stay in place across system updates.

### Install

Copy `whisper-frame-0.2.0-aarch64.tar.gz` to the Frame, then from a terminal in the desktop session:

```sh
tar -xzf whisper-frame-0.2.0-aarch64.tar.gz
cd whisper-frame-0.2.0
./install.sh
```

The archive is about 46 MB and contains the aarch64 Vulkan build of whisper.cpp 1.9.4. The installer downloads `ggml-small-q8_0.bin` (264,464,607 bytes) from the whisper.cpp Hugging Face repo if you do not already have it. Vulkan, PipeWire, and XTest come with SteamOS.

Installed paths:

- `~/.local/bin/whisper-ptt`
- `~/.local/lib/whisper-frame/` (`whisper-cli` and its libraries, RPATH `$ORIGIN`)
- `~/.local/share/whisper/ggml-small-q8_0.bin`
- `~/.config/systemd/user/whisper-ptt.service`

The archive includes the window mic. `install.sh` builds `overlay_point.so` with `gcc` and enables `whisper-panel`. That adds:

- `~/.local/bin/whisper-panel`
- `~/.local/lib/whisper-frame/overlay_point.so`
- `~/.config/systemd/user/whisper-panel.service`

### Use

Hold the headset Select button for about a third of a second. The beep means recording has started. Speak, then release. The transcript is typed into the focused window. A short click is left for Steam Input and does not beep.

Each floating window has a mic at its bottom-right. Hold it to dictate immediately, then release to type into that window. A click shorter than about a third of a second leaves recording running until the next click. While a take is recording, every mic shows a circle. After release they show a spinner until the transcript has been typed. Select drives the same icons.

`clear` and `submit` are commands when they are the whole transcript, or the first or last word.

- `clear` backspaces the characters whisper typed into the field.
- `submit` presses Enter.
- `clear buy milk submit` clears, types `buy milk`, then presses Enter.
- A `clear` or `submit` in the middle of the sentence is typed as a normal word.

### Config

`~/.config/whisper-ptt/config` is created on first run.

```
button=select
language=en
threads=4
append_space=yes
enter=no
min_ms=280
arm_ms=300
max_ms=28000
silence_rms=30
```

`button` is `select`. `both` means the same thing. A gamepad name (`a`, `b`, `x`, `y`, `lb`, `rb`, `view`, `menu`, `guide`, `l3`, `r3`) still arms that button if you set it. The window mic does not use this setting. `arm_ms` is how long a Select hold lasts before the beep. A shorter Select click stays with Steam Input. After editing the file:

```sh
systemctl --user restart whisper-ptt
```

### Uninstall

```sh
systemctl --user disable --now whisper-ptt
systemctl --user disable --now whisper-panel
rm -f ~/.local/bin/whisper-ptt ~/.local/bin/whisper-panel
rm -f ~/.config/systemd/user/whisper-ptt.service ~/.config/systemd/user/whisper-panel.service
rm -rf ~/.local/lib/whisper-frame
systemctl --user daemon-reload
```

Skip the `whisper-panel` lines when that service was never installed.

The model in `~/.local/share/whisper/` is left in place.

### Build the archive

On the Frame, from this repository, with the Vulkan whisper.cpp build at `~/.local/src/whisper.cpp/build-vk`:

```sh
scripts/pack.sh
```

That writes `dist/whisper-frame-<version>-aarch64.tar.gz` from the local binaries. `patchelf` has to be installed. `WHISPER_CPP_BIN` overrides the build directory.

### License

The installer, the services, `whisper-ptt`, and `whisper-panel` are MIT, in `LICENSE`. The bundled `whisper-cli` and ggml libraries are whisper.cpp, also MIT, in `LICENSES/whisper.cpp`.
<!-- /generated:upstream -->
