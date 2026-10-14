---
title: Mouse cursor fix
emoji: 🖱️
category: Convenience
tier: core
summary: Makes the mouse pointer visible in desktop mode
what: Makes the mouse pointer visible in desktop mode.
why: >-
  In desktop mode on the Frame, the mouse moves but its pointer isn't shown: the desktop draws it
  on a separate layer that the headset's view leaves out.
author: >-
  curiousjtuber (steam-frame-utils), originally ThrillSeeker via Cas and Chary XR
source:
  relation: from
  url: https://github.com/curiousjtuber/steam-frame-utils
icon: {theme: input-mouse}
changes: "`~/.config/environment.d/` (one setting for the desktop)"
access: –
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall cursor`, then reboot"
test: {offline: true}
---
# Mouse cursor fix

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Makes the mouse pointer visible in desktop mode.

**Why on a Steam Frame:** In desktop mode on the Frame, the mouse moves but its pointer isn't shown: the desktop draws it on a separate layer that the headset's view leaves out.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install cursor
```

Then reboot (logging out of desktop mode and back in also works). Nothing else to do: after
that, the pointer shows in desktop mode.

## How it works
KWin, the desktop's window manager, normally draws the pointer on a separate hardware layer,
which the headset's view doesn't show. The tweak sets `KWIN_FORCE_SW_CURSOR=1` in
`~/.config/environment.d/90-kwin-software-cursor.conf`, which makes KWin draw the pointer into
the picture itself.

To check it's active, run this in a desktop-mode terminal; it should print
`KWIN_FORCE_SW_CURSOR=1`:

```sh
env | grep KWIN
```

Removing it also takes effect after a reboot.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.config/environment.d/` (one setting for the desktop)
- **Undo:** `./install.sh uninstall cursor`, then reboot
<!-- /generated:changes -->

## Credits
From [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils),
via Cas and Chary XR's "Steam Frame: 10 Things To Do FIRST", credited there to ThrillSeeker.
See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status cursor` · Remove: `./install.sh uninstall cursor`
