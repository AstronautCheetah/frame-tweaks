---
title: Pick up when floating
emoji: ✋
category: VR environment
tier: core
summary: >-
  "Float in World" also picks the window up for placing, like grabbing its bar; your next click
  (or letting go of the trigger) puts it down
what: >-
  "Float in World" also picks the window up, as grabbing the bar under it does, so you place it
  in one go; your next click (or letting go of the trigger, if you're still holding it) puts it
  down.
why: >-
  Floating a window and then grabbing its bar to place it takes two clicks; this makes it one.
author: Frame Tweaks
depends: [vr-dashboard]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks
  that code each time SteamVR starts and switches itself off if it changed (shown in its status)
  until a Frame Tweaks update catches up.
icon: {theme: transform-move}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-grab.js`), via VR
  dashboard patching (helper)
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that
  changed
undo: "`./install.sh uninstall float-grab` (or untick it in the installer window)"
test: {offline: true}
---
# Pick up when floating

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
"Float in World" also picks the window up, as grabbing the bar under it does, so you place it in one go; your next click (or letting go of the trigger, if you're still holding it) puts it down.

**Why on a Steam Frame:** Floating a window and then grabbing its bar to place it takes two clicks; this makes it one.
<!-- /generated:intro -->

Normally **Float in World** leaves the window where it was, and you then grab the bar under it
to place it. With this tweak, Float in World **picks the window up right away**, exactly as
grabbing that bar does: it follows your controller until you put it down.


- **Put it down** with your next click, or by letting go of the trigger if you're still holding
  the click that pressed Float in World. The laser stays on the button that is now **Return to
  Dashboard**; while you hold the window and for 1.5 s after, that button is ignored for it, so
  the click that puts it down can't send it back. (Press it again afterwards to dock it.)
- It follows the controller that pressed the button.
- Switch it on or off by ticking **Pick up when floating** in the installer window's
  **VR environment** group. It works well with [Back to the previous window](../float-return/).
- **Restart SteamVR once** if [VR dashboard patching](../vr-dashboard/) was installed with it.

## How it works
One small patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/).
When a window's dock location changes from the dashboard to the world (what Float in World
does), it starts the dashboard's own drag (`startFloatingWindowMove`, what the bar under a
floating window uses) for the controller the dashboard says is pointing at it. The drag ends the
stock way, on a click; and because the Float in World press comes from SteamVR itself rather than
the page, the patch also ends it when that controller's trigger moves (released, or pressed again).

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
- **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-grab.js`), via VR dashboard patching (helper)
- **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks that code each time SteamVR starts and switches itself off if it changed (shown in its status) until a Frame Tweaks update catches up.
- **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
- **Undo:** `./install.sh uninstall float-grab` (or untick it in the installer window)
<!-- /generated:changes -->

---
Check: `./install.sh status float-grab` · Remove: `./install.sh uninstall float-grab`
