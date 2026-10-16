---
title: Mouse cursor fix
emoji: 🖱️
category: Convenience
tier: core
summary: Makes the mouse pointer visible in desktop mode (SteamOS before 0.5.6)
what: >-
  Makes the mouse pointer visible in desktop mode, on SteamOS before 0.5.6; from 0.5.6, SteamOS
  shows it itself.
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
Makes the mouse pointer visible in desktop mode, on SteamOS before 0.5.6; from 0.5.6, SteamOS shows it itself.

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

## Not needed from SteamOS 0.5.6 (gamescope 3.16.30)
From gamescope 3.16.30, in the SteamOS 0.5.6 beta, SteamVR draws the pointer of the window
under the mouse itself ([gamescope 865e0c1](https://github.com/ValveSoftware/gamescope/commit/865e0c1684),
"keep the cursor out of the composite"). The desktop then shows its pointer without this fix
(checked on a Frame after a restart, October 2026), and with it you get two: the fix's large
one, and a black X (KWin, drawing the pointer itself, leaves its window without one, so SteamVR
draws X's default). How that was found:
[docs/research/mouse-cursor.md](../../../docs/research/mouse-cursor.md).

So on those versions Frame Tweaks doesn't offer it (it's hidden in the list, saying why), and if
it's installed, its status asks you to uninstall it. Older SteamOS versions still get it.

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
