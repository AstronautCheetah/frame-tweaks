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
  SteamVR leaves the dashboard empty where the floated window was, and falls back to Steam when
  the shown window closes. This switches back for you, the way a click on that window's
  dashboard button does.
author: Frame Tweaks
depends: [vr-dashboard]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time
  SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown
  in its status) until a Frame Tweaks update catches up.
icon: {theme: go-previous}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-return.js`), via
  VR dashboard patching (helper)
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer
  fits
undo: >-
  `./install.sh uninstall float-return` (or untick it in the Frame Tweaks window)
test: {offline: true}
---
# Back to the previous window

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
After you float the window the dashboard is showing out into the world, the dashboard shows the window it showed before (after 2.5 s), instead of an empty space; and when the shown window closes, it goes back to the one before instead of Steam.

**Why on a Steam Frame:** SteamVR leaves the dashboard empty where the floated window was, and falls back to Steam when the shown window closes. This switches back for you, the way a click on that window's dashboard button does.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install float-return
```

It brings [VR dashboard patching](../vr-dashboard/) with it if that isn't installed yet. **If
SteamVR was running when that helper was installed, restart SteamVR once** (rebooting is
easiest): SteamVR opens the local port the patch needs only when it starts.
`./install.sh status float-return` says when it's waiting for that.

## Use
Nothing to press. It acts in two cases:

- **You float the shown window out into the world.** After **2.5 seconds** the dashboard shows
  the window you had before, the same as clicking that window's button in the dashboard bar.
  If you dock the window again within that time, or pick another window yourself, it does
  nothing.
- **The shown window closes** (a finished or cancelled [Screen snip](../snip/), say). Instead
  of falling back to Steam, the dashboard goes straight back to the window before it.

It only goes back to a window that is still in the dashboard. If there's none, the dashboard
behaves as usual. Untick it and it stops in the running dashboard within a few seconds. It
works well with [Pick up when floating](../float-grab/).

## How it works
One small patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/).
It keeps a short list of the windows the dashboard showed. When the shown window moves from the
dashboard to the world, it waits 2.5 s and calls the dashboard's own `switchToFrameInternal()`
with the most recent earlier window that is still in the dashboard. When the shown window
closes, it makes the same choice in place of the dashboard's own (which is usually Steam).

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer fits
- **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-return.js`), via VR dashboard patching (helper)
- **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown in its status) until a Frame Tweaks update catches up.
- **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
- **Undo:** `./install.sh uninstall float-return` (or untick it in the Frame Tweaks window)
<!-- /generated:changes -->

---
Check: `./install.sh status float-return` · Remove: `./install.sh uninstall float-return`
