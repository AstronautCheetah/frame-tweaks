---
title: Desktop & VR Recovery
emoji: 🛠️
category: System
tier: core
summary: "Brings back a desktop-mode taskbar that has gone missing, and a VR session whose Steam stopped starting"
what: >-
  Brings back the desktop-mode taskbar (and system tray) when it has gone missing. A small watch
  starts it again by itself when it closes while desktop mode runs, and one button, **Restart
  taskbar**, does it by hand (`restart-plasmashell`), also for a frozen one. And one command,
  `recover-session`, brings back a VR session left with only the room or the backdrop in the
  headset, without a reboot.
why: >-
  In the Frame's nested desktop, nothing restarts a closed taskbar, and it has to be relaunched
  inside that session. SteamOS's graphics layer for desktop apps sometimes gets the taskbar
  disconnected (a SteamOS bug, not something you did). In VR, when the session's D-Bus goes down
  (SteamOS 0.5.7's beta does this as VLC starts), Steam keeps failing to start until a reboot.
author: Frame Tweaks
icon: {theme: tools}
run: {label: Restart taskbar}
processes: ['^[^ ]*python3 ~/.local/bin/taskbar-guard$']
changes: >-
  `~/.local/bin/restart-plasmashell`, `~/.local/bin/taskbar-guard`, its autostart entry
  `~/.config/autostart/frame-tweaks-taskbar-guard.desktop`, and `~/.local/bin/recover-session`
access: –
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall tools`"
test: {offline: true}
---
# Desktop & VR Recovery

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Brings back the desktop-mode taskbar (and system tray) when it has gone missing. A small watch starts it again by itself when it closes while desktop mode runs, and one button, **Restart taskbar**, does it by hand (`restart-plasmashell`), also for a frozen one. And one command, `recover-session`, brings back a VR session left with only the room or the backdrop in the headset, without a reboot.

**Why on a Steam Frame:** In the Frame's nested desktop, nothing restarts a closed taskbar, and it has to be relaunched inside that session. SteamOS's graphics layer for desktop apps sometimes gets the taskbar disconnected (a SteamOS bug, not something you did). In VR, when the session's D-Bus goes down (SteamOS 0.5.7's beta does this as VLC starts), Steam keeps failing to start until a reboot.
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

### A VR session that won't come back
If the headset shows only the room or the backdrop, with no Steam menus, and nothing brings them
back, run in a terminal (over SSH from another computer, or in desktop mode's Konsole):

```sh
recover-session
```

It does only what's needed, and says what it did:

1. **Puts the session's display settings back** when they're gone, copied from SteamVR's server,
   which still runs with them (when it doesn't, just the display, gamescope's first one).
   Without them Steam can't find its display and stops at once, again and again.
2. **Clears the failed services** (Steam's, the wallet's background service) and waits until Steam
   stays up.
3. **Restarts SteamVR**, so its dashboard and the overlays start clean, then waits for Steam
   again (the restart can take the display settings with it). `recover-session --keep-steamvr`
   leaves it running.
4. **Reconnects Bluetooth headphones that came back for calls only** (they say "Call ended" every
   half minute, and sound flat): connected again, they play in high quality.

If it can't (the session's settings are all gone, or Steam still won't start), it says so: then
restart the Frame.

#### Why the session breaks
On SteamOS 0.5.7's beta, launching VLC (the Flatpak) in VR ran the session's D-Bus out of file
descriptors within two seconds: VLC's D-Bus filter (`xdg-dbus-proxy`) opened hundreds of
connections to it. The bus went down, and every program on it stopped, Steam's interface too.
The login manager then started the session's script again, which removes the display setting
and leaves putting it back to gamescope; gamescope was still running, so nothing did, and each
new Steam found no display. Headphones that reconnected meanwhile
found no high-quality audio profile to use. It's a SteamOS bug, not Frame Tweaks'.

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
- **Restart taskbar** only works while desktop mode is running; otherwise it says it found no
  Plasma session. `recover-session` only works while the VR session runs.
- Installed while desktop mode runs, the watch starts at once; otherwise with the next desktop
  mode.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/restart-plasmashell`, `~/.local/bin/taskbar-guard`, its autostart entry `~/.config/autostart/frame-tweaks-taskbar-guard.desktop`, and `~/.local/bin/recover-session`
- **Undo:** `./install.sh uninstall tools`
<!-- /generated:changes -->

## Credits
The nested-session environment trick is based on [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s documentation of the Frame's two sessions. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status tools` · Remove: `./install.sh uninstall tools`
