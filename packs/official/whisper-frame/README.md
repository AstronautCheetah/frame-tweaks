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
---
# whisper-frame: dictate into any window

[groffta/whisper-frame](https://github.com/groffta/whisper-frame) adds two ways to dictate,
typed into the focused window:

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
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
