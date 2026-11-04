# Tray icon flood: research and decisions

For maintainers and reviewers; not shown in the app. Why launching VLC in the VR session took the
whole session down on SteamOS 0.5.7's beta, and why [Tray icon crash fix](../../packs/core/tray-host/)
is the general answer. Measured on 4 November 2026 on one Frame (SteamOS 0.5.7 beta, Flatpak
`org.videolan.VLC` 3.0.24 on runtime `org.kde.Platform` 5.15-25.08).

## Decision

Run a minimal tray watcher (`org.kde.StatusNotifierWatcher`, saying a tray host is there) on the
VR session's D-Bus, as a user service started with the session. Apps then register their tray
icon once and stop retrying. No icon is shown anywhere: nothing in the VR session draws a tray.

## What changed in SteamOS

`/usr/lib/steamos/gamescope-session`, the script that starts the VR session, now does
`export QT_QPA_PLATFORMTHEME=kde` ("Make Qt apps use the styling and behaviour of the desktop
session"). Every Qt app started in the VR session gets it.

## The mechanism

- With the KDE platform theme, a Qt 5 app's tray icon (`QSystemTrayIcon`) goes through the theme's
  D-Bus tray: the StatusNotifierItem protocol, which needs a watcher (`org.kde.StatusNotifierWatcher`
  on the session bus) and, behind it, a host that draws the icons.
- The VR session has neither: nothing owns `org.kde.StatusNotifierWatcher` on its bus.
- The app keeps trying, and each try opens a **new session-bus connection that is never closed**.
  VLC logged 121 `QSystemTrayIcon::setVisible: No Icon set` warnings, one per new connection:
  about 600 connections in 3 s through its Flatpak's `xdg-dbus-proxy`.
- The user bus (`dbus-broker`, limited to 1024 file descriptors) died about 4 s after VLC
  started. Steam and every other program on the bus went with it, and so did the VR session
  (what was left behind, and how to bring it back without a reboot: `recover-session`,
  [Desktop & VR Recovery](../../packs/core/tools/)).

Desktop mode is a Plasma session nested in the VR session, with a bus of its own
([DESIGN.md](../DESIGN.md), "Two sessions at once"); Plasma's own watcher is there, so apps
started in desktop mode were never affected, and a watcher on the VR session's bus can't collide
with it.

## Measurements

VLC launched in the VR session, a watchdog counting the bus proxy's open file descriptors and
killing VLC at 300:

| Setup | Peak fds | Result |
|---|---|---|
| As SteamOS starts it (KDE theme) | 325 | Killed by the watchdog (the bus would have died) |
| `vlc --no-qt-system-tray` | 83 | Fine, no tray icon asked for |
| `QT_QPA_PLATFORMTHEME` cleared | 83 | Fine, Qt's own (X11) tray path |
| KDE theme, tray icon on, a minimal watcher on the bus (`IsStatusNotifierHostRegistered` true) | 87 | Fine: VLC registered one item, no flood |

## Workarounds, and why this one

- **`--no-qt-system-tray`** (or VLC's own setting): VLC only, and every other Qt 5 app with a
  tray icon would still do it.
- **Clearing `QT_QPA_PLATFORMTHEME`** for apps: undoes what Valve wanted (apps styled as on the
  desktop), and has to reach every way an app is started (Steam, menus, Flatpak overrides).
- **A watcher on the bus:** one small service, any app, nothing else changed. It only answers
  the protocol: it keeps the list of registered items (dropping those whose app left the bus) and
  says a host is there. Its name is owned with replacement allowed, and queued: a program that
  asks to replace it (`RequestName` with `REPLACE_EXISTING`) gets it, and the service waits in
  the queue and owns it again once that program lets it go. KDE's own watcher wouldn't replace
  it: kded asks for the name without `REPLACE_EXISTING`, so it would only queue behind the
  service, and plasmashell doesn't own the watcher name at all (it's a host).

## Revisit when

- SteamOS stops setting `QT_QPA_PLATFORMTHEME=kde` in the VR session, or ships a watcher of its
  own there (one that started first would own the name and this service would only wait in the
  queue; one that started later would queue behind it): the tweak would then no longer be
  needed.
- A Qt 6 app, or another toolkit's, floods the same way: only VLC (Qt 5) was measured. The
  watcher answers them alike, as the protocol is the same.
