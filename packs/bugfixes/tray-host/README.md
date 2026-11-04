---
title: Tray icon crash fix
emoji: 🛟
category: System
tier: core
summary: Keeps apps with a tray icon, such as VLC, from taking the VR session down
what: >-
  A small background service that answers apps asking for a tray icon in the VR session, so
  they ask once instead of over and over. The icons aren't shown anywhere: the VR session has no
  tray to show them in.
why: >-
  On SteamOS 0.5.7's beta, Qt apps in the VR session (VLC, for one) look for the desktop's
  tray, find none, and keep trying, each time opening another connection to the session's
  D-Bus. Within seconds the bus runs out of room and goes down, and Steam and the VR session go
  with it.
author: Frame Tweaks
icon: {theme: preferences-desktop-notification}
run: {label: Restart}
changes: >-
  `~/.local/bin/frame-tweaks-tray-host`, user service `frame-tweaks-tray-host` (runs with the VR
  session)
access: –
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall tray-host`"
test: {offline: true}
---
# Tray icon crash fix

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
A small background service that answers apps asking for a tray icon in the VR session, so they ask once instead of over and over. The icons aren't shown anywhere: the VR session has no tray to show them in.

**Why on a Steam Frame:** On SteamOS 0.5.7's beta, Qt apps in the VR session (VLC, for one) look for the desktop's tray, find none, and keep trying, each time opening another connection to the session's D-Bus. Within seconds the bus runs out of room and goes down, and Steam and the VR session go with it.
<!-- /generated:intro -->

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install tray-host
```

Nothing else to do: its service starts right away if the VR session is running, and with the VR
session from then on.

## Use

There's nothing to open. With it installed, start VLC (or another app with a tray icon) in VR as
usual: it opens instead of taking Steam and the headset's view down a few seconds later.

If you ever need it, **▶ Restart** in the Frame Tweaks window restarts the service.

## How it works

Apps put their icon in the tray through a protocol on D-Bus (StatusNotifierItem): they hand it
to a *watcher*, which passes it to whatever draws the tray. Since SteamOS 0.5.7's beta, the VR
session makes Qt apps use KDE's settings, tray included, but nothing there answers as the
watcher. Such an app keeps trying, and every try leaves another bus connection open: VLC opened
about 600 in 3 seconds, and the session's bus, limited to 1024, went down with everything on it.

This tweak's service (`frame-tweaks-tray-host`) is that watcher, on the VR session's bus. It
takes the icons apps register, keeps their list until each app quits, and says a tray is there;
it draws nothing. The details, with the measurements: [docs/research/tray-icon-flood.md](../../../docs/research/tray-icon-flood.md).

Desktop mode has its own tray (Plasma's taskbar) on a bus of its own, so apps started there are
unaffected, and the service never gets in its way. If another program in the VR session asks to
take the watcher's place, it gets it, and the service waits until that program lets it go, then
answers again.

## Good to know

- **Hiding into the tray hides for good:** an app set to go to the tray when its window closes
  (some chat apps do) now believes it has one. In the VR session, closing its window leaves it
  running with no window; start it again to get the window back, or turn that setting off.
- Without it, VLC also starts fine with its tray icon turned off (VLC: Tools → Preferences →
  Interface → *Show systray icon*, or `--no-qt-system-tray`), but only VLC.
- If the VR session already went down this way, [Desktop & VR Recovery](../../core/tools/)'s
  `recover-session` brings it back without a reboot.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/frame-tweaks-tray-host`, user service `frame-tweaks-tray-host` (runs with the VR session)
- **Undo:** `./install.sh uninstall tray-host`
<!-- /generated:changes -->

## Credits
Frame Tweaks. The protocol is freedesktop.org's
[StatusNotifierItem](https://www.freedesktop.org/wiki/Specifications/StatusNotifierItem/), as
KDE implements it.

---
Check: `./install.sh status tray-host` · Remove: `./install.sh uninstall tray-host`
