---
title: ydotool (helper)
emoji: ⌨️
category: System
tier: helper
summary: Lets other tweaks type into any app; installed automatically when needed
what: >-
  The virtual keyboard that Dictation, Arrow Pad and Scroll strips type through. Installed
  automatically with them.
why: >-
  On the Frame's desktop (KDE Plasma on Wayland), ordinary programs can't send key presses to
  other apps. ydotool can: it adds a virtual keyboard to the kernel (`/dev/uinput`), which every
  app treats as a real one.
author: ReimuNotMoe (ydotool)
source: {relation: uses, url: https://github.com/ReimuNotMoe/ydotool}
icon: {theme: input-keyboard-virtual}
run: {label: Restart}
changes: >-
  `ydotool` and `ydotoold` in `~/.local/bin` (Arch Linux ARM package, signature-checked), user
  service `ydotoold`
access: >-
  **Writes to `/dev/uinput`** (a virtual keyboard any program you run could use while it's
  running)
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall ydotool` (after the tweaks that use it)"
test: {offline: true}
---
# ydotool (helper)

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
The virtual keyboard that Dictation, Arrow Pad and Scroll strips type through. Installed automatically with them.

**Why on a Steam Frame:** On the Frame's desktop (KDE Plasma on Wayland), ordinary programs can't send key presses to other apps. ydotool can: it adds a virtual keyboard to the kernel (`/dev/uinput`), which every app treats as a real one.
<!-- /generated:intro -->

## Install

You don't need to tick it: it's installed automatically with [Dictation](../dictation/),
[Arrow Pad](../arrowpad/) or [Scroll strips](../scroll-strips/). To install it on its own, tick
it in the Frame Tweaks window, or:

```sh
./install.sh install ydotool
```

Nothing else to do: its background service starts right away and at every login. It needs write
access to `/dev/uinput`, which SteamOS normally gives to the `input` group; if it's missing, the
install stops and says so.

## Use

There's nothing to open. Other tweaks type through it:

| Tweak | How it uses ydotool |
|---|---|
| [Dictation](../dictation/) | Types the text Whisper heard into the window you're using, one letter at a time, as if you'd typed it. The text is also copied, so you can paste it instead (set `DICTATE_NOTYPE=1` to only copy). |
| [Arrow Pad](../arrowpad/) | Each button sends a real key press and release (arrows, Esc, Home/End, F-keys, Ctrl+C/V for Copy/Paste…). Holding a button holds the key, so key repeat works. The pad never takes the keyboard focus, so the keys go to the app you were using. Its **Tools → 🎤** button starts and stops Dictation. |
| [Scroll strips](../scroll-strips/) | Windows other than the desktop scroll with arrow keys (PgUp/PgDn for a whole page) sent through ydotool. |

If typing stops working, press **▶ Restart** in the Frame Tweaks window. It restarts the
`ydotoold` service.

## How it works

`ydotoold` is a small background service (a systemd user service). It creates a virtual keyboard
through the kernel's `/dev/uinput` and listens on a socket only you can use,
`/run/user/<your user id>/.ydotool_socket`. Tweaks send it key presses, and apps receive them
like keys from a real keyboard. The simpler tool, `xdotool`, only reaches older X11 windows, not
Wayland ones.

The service runs sandboxed: no network, your home folder read-only, and only its socket folder
writable. The programs come from [Arch Linux ARM](https://archlinuxarm.org)'s package, checked
against its signing key. If a newer package doesn't run on your SteamOS version, the one you
already have is kept.

## Good to know

- While `ydotoold` runs, any program you run could type through it too. That's the access
  listed below.
- You can't remove it while a tweak that needs it is installed: uninstall that tweak first.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `ydotool` and `ydotoold` in `~/.local/bin` (Arch Linux ARM package, signature-checked), user service `ydotoold`
- **Unusual access:** **Writes to `/dev/uinput`** (a virtual keyboard any program you run could use while it's running)
- **Undo:** `./install.sh uninstall ydotool` (after the tweaks that use it)
<!-- /generated:changes -->

## Credits
[ydotool](https://github.com/ReimuNotMoe/ydotool) (AGPL-3.0) by ReimuNotMoe, from [Arch Linux ARM](https://archlinuxarm.org)'s package, not modified. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status ydotool` · Remove: `./install.sh uninstall ydotool`
