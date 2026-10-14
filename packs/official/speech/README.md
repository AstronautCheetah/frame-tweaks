---
title: Speech engine (helper)
emoji: 🗣️
category: System
tier: helper
summary: >-
  Gives the Frame a voice: Piper for Narrate, and espeak-ng for Orca and other speech-dispatcher
  apps
what: >-
  Gives the Frame a voice: Piper (offline, natural) for Screen snip's Narrate, and espeak-ng for
  Orca and other apps that speak through speech-dispatcher. Installed automatically.
why: >-
  SteamOS ships speech-dispatcher and its espeak-ng module, but not espeak-ng itself, so nothing
  can speak (the Screen reader's Orca was silent).
author: RHASSPY (Piper); espeak-ng contributors
source: {relation: uses, url: https://github.com/rhasspy/piper}
icon: {theme: audio-speakers-symbolic}
changes: >-
  Piper and a voice in `~/.local/share/frame-tweaks/speech` (checksum-pinned),
  `~/.config/speech-dispatcher/speechd.conf` (backed up, restored on uninstall)
access: None beyond your home folder
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall speech` (after Screen snip and Screen reader)"
---
# Speech engine (helper)

SteamOS includes **speech-dispatcher** (the service Orca and other apps speak through) and its
**espeak-ng** module, but not espeak-ng itself, so nothing can actually speak: the
[Screen reader](../screen-reader/)'s Orca is silent. This helper fixes that, and provides the
voice for [Screen snip](../snip/)'s **Narrate**. It's installed automatically with them.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** Piper and a voice in `~/.local/share/frame-tweaks/speech` (checksum-pinned), `~/.config/speech-dispatcher/speechd.conf` (backed up, restored on uninstall)
> - **Unusual access:** None beyond your home folder
> - **Undo:** `./install.sh uninstall speech` (after Screen snip and Screen reader)
<!-- /generated:glance -->

- **[Piper](https://github.com/rhasspy/piper)** (MIT), a fast offline neural voice, with the
  **LJ Speech** voice (its dataset is public domain): used by Narrate. Pinned by checksum
  ([`pin`](pin), [`voice.pin`](voice.pin), [`voice-config.pin`](voice-config.pin)).
- **espeak-ng**, which comes inside Piper's download: speech-dispatcher's own espeak-ng module is
  run with it (a small wrapper sets the library and data paths), through a user
  `~/.config/speech-dispatcher/speechd.conf` made from SteamOS's (yours is backed up and put back
  on uninstall). Orca uses it; espeak-ng is quick, which suits a screen reader.
- Test: `spd-say "hello"`. Orca's voice settings: **System Settings → Accessibility → Screen Reader**.

---
Check: `./install.sh status speech` · Remove: `./install.sh uninstall speech`
