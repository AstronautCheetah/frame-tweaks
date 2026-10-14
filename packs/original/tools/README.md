---
title: Desktop Recovery
emoji: 🛠️
category: System
tier: core
summary: "An as-needed fix for a desktop whose taskbar has gone missing: one button brings it back"
what: >-
  An as-needed fix for a desktop-mode desktop whose taskbar (and system tray) has gone missing:
  one button, **Restart taskbar**, brings them back (`restart-plasmashell`).
why: >-
  In the Frame's nested desktop, nothing restarts a crashed taskbar automatically, and it has to
  be relaunched inside that session.
author: Frame Tweaks
icon: {theme: tools}
run: {label: Restart taskbar}
changes: "`~/.local/bin/restart-plasmashell`"
access: –
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall tools`"
test: {offline: true}
---
# Desktop Recovery

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
An as-needed fix for a desktop-mode desktop whose taskbar (and system tray) has gone missing: one button, **Restart taskbar**, brings them back (`restart-plasmashell`).

**Why on a Steam Frame:** In the Frame's nested desktop, nothing restarts a crashed taskbar automatically, and it has to be relaunched inside that session.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install tools
```

## Use
If the taskbar or system tray in desktop mode disappears (Plasma's `plasmashell` crashed), press
**Restart taskbar** on this tweak's row, or run in a terminal:

```sh
restart-plasmashell
```

If `plasmashell` is still running, it's closed and started again, so this also helps when the
taskbar is frozen rather than gone (a frozen one that doesn't close within 5 seconds is killed).

## How it works
In the Frame's nested desktop, `plasmashell` isn't a systemd service, so nothing restarts it
after a crash. It also has to be started with the desktop session's own environment and D-Bus.
`restart-plasmashell` copies them from the session manager (`ksmserver`) and starts
`plasmashell` with them. Its output goes to `/run/user/<your user id>/plasmashell.log`.

## Good to know
- It only works while desktop mode is running; otherwise it says it found no Plasma session.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/restart-plasmashell`
- **Undo:** `./install.sh uninstall tools`
<!-- /generated:changes -->

## Credits
The nested-session environment trick is based on [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s documentation of the Frame's two sessions. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status tools` · Remove: `./install.sh uninstall tools`
