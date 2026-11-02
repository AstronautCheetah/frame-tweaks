---
title: Cuff
emoji: ⌚
category: VR environment
tier: extras
summary: A wrist panel in VR with the time, batteries, quick actions and tabs
what: >-
  Look at the back of your wrist in VR and a panel is there: the time, the headset's, the
  controllers' and Bluetooth headphones' batteries, six quick actions (dictation, mic mute,
  passthrough, recenter, the SteamVR keyboard, a screenshot), and tabs for what's playing, audio,
  a timer and performance. Touch it with the sphere in front of your other controller.
why: >-
  The Frame has no glanceable status in VR: the time and batteries are behind the dashboard.
  Linked: [Cuff](https://github.com/Brobert-in-aus/cuff) installs itself on the Frame, the way its
  README describes, at the commit Frame Tweaks tried it at.
author: Brobert-in-aus (Cuff)
source:
  relation: from
  url: https://github.com/Brobert-in-aus/cuff
experimental: >-
  A new project (October 2026), installed at the commit Frame Tweaks tried it at. Its dictation
  overlaps with Frame Tweaks' Dictation, and it downloads its own speech model (about 650 MB) on
  install.
icon: {theme: chronometer}
link:
  install: >-
    if [ -x ~/.local/bin/dictate ] && ! grep -qs '^\[dictation\]' ~/.config/cuff/config.toml; then
    mkdir -p ~/.config/cuff && printf '%s\n' '' '# Frame Tweaks Dictation instead of a model of its own (written by Frame Tweaks)'
    '[dictation]' 'command = ["~/.local/bin/dictate", "--ptt"]' 'env = { DICTATE_STATUS = "stdout" }' 'local = false'
    >> ~/.config/cuff/config.toml || exit; fi;
    d=$(mktemp -d) && trap 'rm -rf "$d"' EXIT &&
    curl -fsSL https://github.com/Brobert-in-aus/cuff/archive/bea0789859d3d6ae3d1972dc91189544e7f831b9.tar.gz | tar -C "$d" -xzf - &&
    sh "$d"/cuff-bea0789859d3d6ae3d1972dc91189544e7f831b9/install.sh --here &&
    echo bea0789 > ~/.local/share/cuff/frame-tweaks-commit
  uninstall: >-
    systemctl --user disable --now cuff; rm -rf ~/.local/share/cuff ~/.cache/cuff
    ~/.config/systemd/user/cuff.service ~/.config/systemd/user/cuff.service.d;
    systemctl --user daemon-reload
  installed: ~/.config/systemd/user/cuff.service
  version: cat ~/.local/share/cuff/frame-tweaks-commit 2>/dev/null || echo unknown
  readme: https://github.com/Brobert-in-aus/cuff#readme
changes: >-
  What Cuff's own installer sets up: its app and a Python venv in `~/.local/share/cuff` (with
  its on-headset speech model, about 650 MB, in `~/.cache`), and a user service
  (`cuff.service`) that starts it at login and keeps it running. Settings go in
  `~/.config/cuff/config.toml` (kept on uninstall)
access: >-
  A SteamVR overlay; reads the headset's and controllers' batteries; its quick actions change
  passthrough, recenter, mute the mic and take screenshots; its dictation records the microphone
survives_updates: Yes (everything is in your home folder)
undo: "Uncheck it, or `./install.sh uninstall cuff`: Cuff's own uninstall (keeps `~/.config/cuff`)"
---
# Cuff

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Look at the back of your wrist in VR and a panel is there: the time, the headset's, the controllers' and Bluetooth headphones' batteries, six quick actions (dictation, mic mute, passthrough, recenter, the SteamVR keyboard, a screenshot), and tabs for what's playing, audio, a timer and performance. Touch it with the sphere in front of your other controller.

**Why on a Steam Frame:** The Frame has no glanceable status in VR: the time and batteries are behind the dashboard. Linked: [Cuff](https://github.com/Brobert-in-aus/cuff) installs itself on the Frame, the way its README describes, at the commit Frame Tweaks tried it at.
<!-- /generated:intro -->

Frame Tweaks runs [Cuff](https://github.com/Brobert-in-aus/cuff)'s own installer at the commit
it was tried at (bea0789, 2026-10-25).

## Before trying it
- **One dictation.** With Frame Tweaks' Dictation installed first, Cuff's dictation button uses
  it: the same engine (Whisper or Parakeet), language, history and typing, and Cuff's own speech
  model isn't loaded. Installing Cuff adds a `[dictation]` section to `~/.config/cuff/config.toml`
  saying so, unless that file already has one. Delete the section to go back to Cuff's own model.
  Cuff's installer still downloads its model (about 650 MB): it doesn't offer to skip it yet.
- **Its PC half** (Cuff for PC, Windows) is optional: without it, Cuff dictates on the headset and
  the Performance tab's PC fields say so.
- **It runs all the time** once installed (a user service at login, restarted if it stops), not
  only with SteamVR. Its log: `journalctl --user -u cuff -f`.
- **Charms** (its tabs) are Python running inside Cuff: add only ones you trust.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** What Cuff's own installer sets up: its app and a Python venv in `~/.local/share/cuff` (with its on-headset speech model, about 650 MB, in `~/.cache`), and a user service (`cuff.service`) that starts it at login and keeps it running. Settings go in `~/.config/cuff/config.toml` (kept on uninstall)
- **🧪 Experimental:** A new project (October 2026), installed at the commit Frame Tweaks tried it at. Its dictation overlaps with Frame Tweaks' Dictation, and it downloads its own speech model (about 650 MB) on install.
- **Unusual access:** A SteamVR overlay; reads the headset's and controllers' batteries; its quick actions change passthrough, recenter, mute the mic and take screenshots; its dictation records the microphone
- **Undo:** Uncheck it, or `./install.sh uninstall cuff`: Cuff's own uninstall (keeps `~/.config/cuff`)
<!-- /generated:changes -->
