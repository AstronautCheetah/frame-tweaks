---
name: Core
author: Frame Tweaks
api: 1
categories: [Accessibility, Convenience, VR environment, System, Hardware, Privacy & security, Developer]
order:
  - dictation
  - arrowpad
  - snip
  - adb-scrcpy
  - vr-dashboard
  - curvature
  - float-return
  - float-grab
  - scroll-strips
  - wallet
  - firefox
  - homebrew
  - tools
  - ydotool
  - speech
  - charge-limit
---
Frame Tweaks' own fixes and app setups for the Steam Frame, and the helpers many of them need:
other projects' tools, installed with the tweaks that use them and credited to their makers.
Homebrew installs the programs that Dictation, Screen snip and Android Mirror run (whisper.cpp,
tesseract, scrcpy); ydotool types for Arrow Pad, Dictation and Scroll strips; Piper speaks for
Narrate. Each one is tested on a Frame and installed into your home folder, so it survives
SteamOS updates and comes off cleanly (Battery charge limit also adds a udev rule in /etc, which
SteamOS updates keep).

How it's loaded: like any other pack (see [docs/mods.md](../../docs/mods.md)), one folder per
tweak, each described by the front matter of its README.md. Frame Tweaks' other official packs,
[Integrations](../integrations/pack.md) and [3rd Party](../third-party/pack.md), use the same
categories. This file sets the order of the
categories (for all three) and of this pack's tweaks in the installer window, the README and
`./install.sh list`.
