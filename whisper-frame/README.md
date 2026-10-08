# whisper-frame: dictate into any window

[groffta/whisper-frame](https://github.com/groffta/whisper-frame) adds two ways to dictate,
typed into the focused window:

- **Hold the headset's Select button** until the beep, speak, release.
- **Hold the mic under any floating window** (it appears at each window's bottom-right).

```sh
./install.sh whisper-frame
```

**The window mic is off by default.** It tracks every floating window by polling SteamVR's
compositor about 60 times a second; measured on a Frame that costs about 31% of a CPU core
(whisper-panel itself plus extra work in vrwebhelper and vrserver), which showed up as jitter
when turning the head. Turn it on with `WHISPER_FRAME_WINDOW_MIC=1 ./install.sh whisper-frame`.
The Select-button dictation costs nothing while idle.

This installs whisper-frame's **latest upstream release** (checksum-verified, with its own
installer), so updates come from upstream; re-run to update. Two additions:
- **Shared model:** whisper-frame and our [dictation](../dictation/) use the same
  `~/.local/share/whisper/ggml-small-q8_0.bin`, and dictation uses whisper-frame's bundled
  whisper-cli when it's there, so there are no duplicate copies.
- **SteamVR restarts:** if you enable the window mic, a systemd drop-in restarts it together with
  SteamVR (it loses its connection and doesn't recover on its own).

## Credits
whisper-frame is groffta's (MIT); it bundles whisper.cpp (MIT). See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status whisper-frame` · Remove: `./install.sh uninstall whisper-frame`
