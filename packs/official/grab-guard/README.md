---
title: Grab guard
emoji: 🔓
category: System
tier: core
summary: >-
  Warns when desktop mode has taken all input, and how to undo it (tap Right Ctrl)
what: >-
  Tells you when desktop mode has taken all input (windows stop responding) and how to undo it.
why: >-
  A Right Ctrl press makes desktop mode grab every key and click; nothing on screen says so
  except its window title.
author: Frame Tweaks
processes: [~/.local/bin/grab-guard --run]
changes: >-
  `grab-guard`, user service `grab-guard`, a log in `~/.local/state/frame-tweaks/logs`
access: >-
  **Reads every keyboard's key presses**, and the Steam session's display's (only to notice
  Right Ctrl; nothing else is kept)
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall grab-guard`"
---
# Grab guard: notice when desktop mode takes all input

**Problem:** desktop mode on the Frame is a nested KWin running as a window of the Steam session.
**A Right Ctrl press toggles its input grab.** While it's grabbed, every key and click goes to
the desktop: Frame Tweaks, floating windows and the rest stop responding, and nothing says why
except the desktop window's title ("Press right control to **ungrab** input").

<!-- generated:glance (dev/gen-docs.py, from each tweak's README front matter) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `grab-guard`, user service `grab-guard`, a log in `~/.local/state/frame-tweaks/logs`
> - **Unusual access:** **Reads every keyboard's key presses**, and the Steam session's display's (only to notice Right Ctrl; nothing else is kept)
> - **Undo:** `./install.sh uninstall grab-guard`
<!-- /generated:glance -->

**Fix:** a small watcher (`grab-guard`, a user service) checks that title every second. When
the grab turns on it shows a notification: tap **Right Ctrl** on a keyboard once to release it.
It also logs where the Right Ctrl came from, so a stray source can be tracked down: which input
device sent it (a Bluetooth keyboard, the virtual keyboard that Arrow Pad and Dictation type
through, a controller…), and how the Steam session's display got it (also keys that never pass
through an input device: faked by an X program (XTest), or typed through libei, as Full
Keyboard does): `~/.local/state/frame-tweaks/logs/grab-guard.log`, or `grab-guard --status`.

```sh
./install.sh install grab-guard
```

It never sends a key itself: sending Right Ctrl is exactly what flips the grab, and Frame
Tweaks' own key clean-ups (Arrow Pad's Unstick, the stuck-key reset) leave it out for that
reason.

---
Check: `./install.sh status grab-guard` · Remove: `./install.sh uninstall grab-guard`
