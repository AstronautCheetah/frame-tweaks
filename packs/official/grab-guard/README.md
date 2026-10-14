---
title: Grab guard
emoji: 🔓
category: System
tier: core
summary: >-
  Warns you when desktop mode has taken all input, and how to undo it (tap Right Ctrl)
what: >-
  A notification when desktop mode has taken all input, so other windows stop responding, telling
  you how to undo it.
why: >-
  A Right Ctrl press makes the Frame's desktop mode take every key and click. Nothing on screen
  says so except its window title, so everything else just seems frozen.
author: Frame Tweaks
processes: [~/.local/bin/grab-guard --run]
changes: >-
  `grab-guard` in `~/.local/bin`, user service `grab-guard`, a log in
  `~/.local/state/frame-tweaks/logs`
access: >-
  **Reads every keyboard's key presses**, and the keys the Steam session's display receives (only
  to notice Right Ctrl; nothing else is kept)
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall grab-guard` (keeps its log)"
---
# Grab guard

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
A notification when desktop mode has taken all input, so other windows stop responding, telling you how to undo it.

**Why on a Steam Frame:** A Right Ctrl press makes the Frame's desktop mode take every key and click. Nothing on screen says so except its window title, so everything else just seems frozen.
<!-- /generated:intro -->

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install grab-guard
```

Nothing else to do: it starts watching right away, and again at every login.

## Use

On the Frame, desktop mode runs as a window inside the Steam session. **Pressing Right Ctrl
switches its input grab on or off.** While the grab is on, every key and click goes to the
desktop, so Frame Tweaks, floating windows and everything else stop responding. The only sign is
the desktop window's title, which then says "Press right control to **ungrab** input".

When that happens, Grab guard shows a notification: **"Desktop mode took all input"**. To undo
it, tap **Right Ctrl** on a keyboard once.

While the grab is on, this tweak's row in the Frame Tweaks window says so too. In a terminal,
`grab-guard --status` tells you whether the grab is on and shows the last few log lines.

## How it works

`grab-guard` runs as a background service (a systemd user service). Once a second it reads the
desktop window's title to tell whether the grab is on.

It also notes where each Right Ctrl came from, so you can track down a stray one. It watches two
places:

- **Keyboards** (input devices): a Bluetooth keyboard, the virtual keyboard that Arrow Pad and
  Dictation type through, a controller… Newly connected keyboards are picked up within
  30 seconds.
- **The Steam session's display**, which also gets keys that never pass through an input device:
  keys faked by an X program (XTest), or typed through libei, as Full Keyboard and Steam can.

When the grab switches on or off, it writes a line to
`~/.local/state/frame-tweaks/logs/grab-guard.log` naming the source of the last Right Ctrl, if it
saw one in the 10 seconds before. The notification says the same.

## Good to know

- It never sends a key itself: sending Right Ctrl is exactly what switches the grab. For the same
  reason, Frame Tweaks' own key clean-ups (Arrow Pad's **Unstick**, the stuck-key reset) never
  send Right Ctrl.
- If the desktop isn't running, there's nothing to watch, and it waits.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `grab-guard` in `~/.local/bin`, user service `grab-guard`, a log in `~/.local/state/frame-tweaks/logs`
- **Unusual access:** **Reads every keyboard's key presses**, and the keys the Steam session's display receives (only to notice Right Ctrl; nothing else is kept)
- **Undo:** `./install.sh uninstall grab-guard` (keeps its log)
<!-- /generated:changes -->

## Credits
Made for Frame Tweaks. It uses `xwininfo` and `xinput`, which come with SteamOS.

---
Check: `./install.sh status grab-guard` · Remove: `./install.sh uninstall grab-guard`
