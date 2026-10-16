---
title: Desktop Recovery
emoji: 🛠️
category: System
tier: core
summary: "Brings back a desktop-mode taskbar that has gone missing: by itself, or with one button"
what: >-
  Brings back the desktop-mode taskbar (and system tray) when it has gone missing. A small watch
  starts it again by itself when it closes while desktop mode runs, and one button, **Restart
  taskbar**, does it by hand (`restart-plasmashell`), also for a frozen one.
why: >-
  In the Frame's nested desktop, nothing restarts a closed taskbar, and it has to be relaunched
  inside that session. SteamOS's graphics layer for desktop apps sometimes gets the taskbar
  disconnected (a SteamOS bug, not something you did).
author: Frame Tweaks
icon: {theme: tools}
run: {label: Restart taskbar}
processes: ['^[^ ]*python3 ~/.local/bin/taskbar-guard$']
changes: >-
  `~/.local/bin/restart-plasmashell`, `~/.local/bin/taskbar-guard`, and its autostart entry
  `~/.config/autostart/frame-tweaks-taskbar-guard.desktop`
access: –
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall tools`"
test: {offline: true}
---
# Desktop Recovery

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Brings back the desktop-mode taskbar (and system tray) when it has gone missing. A small watch starts it again by itself when it closes while desktop mode runs, and one button, **Restart taskbar**, does it by hand (`restart-plasmashell`), also for a frozen one.

**Why on a Steam Frame:** In the Frame's nested desktop, nothing restarts a closed taskbar, and it has to be relaunched inside that session. SteamOS's graphics layer for desktop apps sometimes gets the taskbar disconnected (a SteamOS bug, not something you did).
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install tools
```

## Use
Nothing to do: while desktop mode runs, a watch (`taskbar-guard`) notices when the taskbar
closes and starts it again a few seconds later. If it closes more than 3 times in 10 minutes, the
watch stops and says so, so a taskbar that can't start doesn't loop.

By hand: if the taskbar or system tray in desktop mode is gone or frozen, press **Restart
taskbar** on this tweak's row, or run in a terminal:

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

`taskbar-guard` starts with desktop mode (KDE autostart, in that session's environment) and ends
with it. It waits on `plasmashell` and desktop mode's KWin without polling. When `plasmashell`
ends while KWin still runs, and no new one has started within 8 seconds (Plasma's own restart,
or the button), it runs `restart-plasmashell`. Its log is in the journal:
`journalctl --user -t taskbar-guard` (or `journalctl -t taskbar-guard`).

### Why the taskbar disappears
SteamOS turns on its graphics layer for desktop apps (Gamescope WSI, `ENABLE_GAMESCOPE_WSI=1`)
for every app in desktop mode. Now and then, as the taskbar's windows get new buffers, that layer
asks KWin for something about an object that's no longer the window it meant. KWin treats that as
a broken app and disconnects it ("invalid arguments for
`wp_linux_drm_syncobj_manager_v1.get_surface`" in the journal, then "The Wayland connection
experienced a fatal error" from `plasmashell`). Other apps can be disconnected the same way;
the taskbar is the one you notice. It's a SteamOS bug, not Frame Tweaks'.

## Good to know
- It only works while desktop mode is running; otherwise it says it found no Plasma session.
- Installed while desktop mode runs, the watch starts at once; otherwise with the next desktop
  mode.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/restart-plasmashell`, `~/.local/bin/taskbar-guard`, and its autostart entry `~/.config/autostart/frame-tweaks-taskbar-guard.desktop`
- **Undo:** `./install.sh uninstall tools`
<!-- /generated:changes -->

## Credits
The nested-session environment trick is based on [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s documentation of the Frame's two sessions. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status tools` · Remove: `./install.sh uninstall tools`
