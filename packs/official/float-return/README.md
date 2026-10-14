---
title: Back to the previous window
emoji: ↩️
category: VR environment
tier: core
summary: >-
  After you float a window out of the dashboard, the dashboard shows the window it showed before
  (after 2.5 s) instead of an empty space
what: >-
  After you float the window the dashboard is showing out into the world, the dashboard shows
  the window it showed before (after 2.5 s), instead of an empty space; and when the shown
  window closes, it goes back to the one before instead of Steam.
why: >-
  SteamVR leaves the dashboard empty where the floated window was; this switches back the way a
  click on that window's dashboard button does.
author: Frame Tweaks
depends: [vr-dashboard]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks
  that code each time SteamVR starts and switches itself off if it changed (shown in its status)
  until a Frame Tweaks update catches up.
icon: {theme: go-previous}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-return.js`), via
  VR dashboard patching (helper)
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that
  changed
undo: >-
  `./install.sh uninstall float-return` (or untick it in the installer window)
test: {offline: true}
---
# Back to the previous window

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
After you float the window the dashboard is showing out into the world, the dashboard shows the window it showed before (after 2.5 s), instead of an empty space; and when the shown window closes, it goes back to the one before instead of Steam.

**Why on a Steam Frame:** SteamVR leaves the dashboard empty where the floated window was; this switches back the way a click on that window's dashboard button does.
<!-- /generated:intro -->

When you **float the window the dashboard is showing** out into the world, SteamVR leaves an
empty space in the dashboard where it was. With this tweak, after **2.5 seconds** the dashboard
shows the window you had before, the same as clicking that window's button in the dashboard bar.

The same when the window the dashboard shows is **closed** (a finished or cancelled
[Screen snip](../snip/), say): instead of falling back to Steam, the dashboard goes back to the
window before it, without Steam showing in between.


- Switch it on or off by ticking **Back to the previous window** in the installer window's
  **VR environment** group (it stops in the running dashboard within a few seconds).
- It only acts right after a float: if you dock the window again within that time, or pick
  another window yourself, it does nothing. Floating a window you opened from a world window,
  or one with nothing shown before it, also leaves the dashboard as it is.
- **Restart SteamVR once** if [VR dashboard patching](../vr-dashboard/) was installed with it.

## How it works
One small patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/).
It keeps a short list of the windows the dashboard showed; when the shown window's dock
location changes from the dashboard to the world, it waits 2.5 s and calls the dashboard's own
`switchToFrameInternal()` with the window before it that is still docked in the dashboard.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
- **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-return.js`), via VR dashboard patching (helper)
- **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks that code each time SteamVR starts and switches itself off if it changed (shown in its status) until a Frame Tweaks update catches up.
- **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
- **Undo:** `./install.sh uninstall float-return` (or untick it in the installer window)
<!-- /generated:changes -->

---
Check: `./install.sh status float-return` · Remove: `./install.sh uninstall float-return`
