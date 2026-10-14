---
title: Speech engine (helper)
emoji: 🗣️
category: System
tier: helper
summary: >-
  Gives the Frame a voice: Piper for Screen snip's Narrate, espeak-ng for Orca and other apps;
  installed with Screen snip
what: >-
  A voice for the Frame: Piper, an offline, natural-sounding voice, for Screen snip's Narrate,
  and espeak-ng for KDE's screen reader (Orca) and other apps that speak through
  speech-dispatcher. Installed automatically with Screen snip.
why: >-
  SteamOS includes speech-dispatcher, the service apps speak through, but no voice for it to use,
  so Orca and other talking apps stay silent.
author: RHASSPY (Piper); espeak-ng contributors
source: {relation: uses, url: https://github.com/rhasspy/piper}
icon: {theme: audio-speakers-symbolic}
changes: >-
  Piper (with espeak-ng) and a voice in `~/.local/share/frame-tweaks/speech` (checksum-pinned); a
  speech-dispatcher setup in `~/.config/speech-dispatcher` (yours backed up, restored on
  uninstall)
access: None beyond your home folder
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall speech` (after Screen snip)"
---
# Speech engine (helper)

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
A voice for the Frame: Piper, an offline, natural-sounding voice, for Screen snip's Narrate, and espeak-ng for KDE's screen reader (Orca) and other apps that speak through speech-dispatcher. Installed automatically with Screen snip.

**Why on a Steam Frame:** SteamOS includes speech-dispatcher, the service apps speak through, but no voice for it to use, so Orca and other talking apps stay silent.
<!-- /generated:intro -->

## Install

You don't need to tick it: it's installed automatically with [Screen snip](../snip/). To install
it on its own (for example, to give Orca a voice), tick it in the Frame Tweaks window, or:

```sh
./install.sh install speech
```

It downloads Piper and its voice (the voice is about 60 MB). Nothing else to do.

## Use

- **Narrate** in [Screen snip](../snip/) reads the text in your snip aloud with Piper's voice.
- **Orca**, KDE's screen reader, and other apps that speak through speech-dispatcher use
  espeak-ng. It sounds more robotic than Piper but starts speaking faster, which suits a
  screen reader. Orca's voice settings are in **System Settings → Accessibility → Screen Reader**.
- To test it from a terminal: `spd-say "hello"`.

## How it works

- **[Piper](https://github.com/rhasspy/piper)** runs entirely on the Frame, with no internet
  needed once it's installed. It uses the **LJ Speech** voice (US English). Both downloads are
  pinned to a checked version and SHA256 ([`pin`](pin), [`voice.pin`](voice.pin),
  [`voice-config.pin`](voice-config.pin)).
- **espeak-ng** comes inside Piper's download. SteamOS already has speech-dispatcher's espeak-ng
  module, just not espeak-ng itself, so a small wrapper runs that module with Piper's copy.
- speech-dispatcher reads a settings file in your home folder in place of the system one. This
  tweak writes `~/.config/speech-dispatcher/speechd.conf`, a copy of SteamOS's with espeak-ng
  added and made the default, plus `modules/espeak-ng.conf` next to it. If you already had these
  files, they're backed up first and put back when you uninstall. It then stops any running
  speech-dispatcher, so the next app that speaks starts it again with the new setup.

## Good to know

- You can't remove it while Screen snip is installed: uninstall Screen snip first.
- After uninstalling, speech-dispatcher is back to SteamOS's setup, which has no voice.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** Piper (with espeak-ng) and a voice in `~/.local/share/frame-tweaks/speech` (checksum-pinned); a speech-dispatcher setup in `~/.config/speech-dispatcher` (yours backed up, restored on uninstall)
- **Unusual access:** None beyond your home folder
- **Undo:** `./install.sh uninstall speech` (after Screen snip)
<!-- /generated:changes -->

## Credits
[Piper](https://github.com/rhasspy/piper) (MIT) by Michael Hansen / RHASSPY, from its official
aarch64 release, not modified. The voice is `en_US-ljspeech-medium` from
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) (MIT), trained on the
[LJ Speech](https://keithito.com/LJ-Speech-Dataset/) dataset (public domain).
[espeak-ng](https://github.com/espeak-ng/espeak-ng) (GPL-3.0) by its contributors, as bundled in
Piper's release. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status speech` · Remove: `./install.sh uninstall speech`
