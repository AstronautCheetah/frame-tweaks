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
  In SteamVR, floating a window and then placing it takes two steps: press Float in World, then
  grab the bar under the window. This makes it one.
author: Frame Tweaks
depends: [vr-dashboard]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time
  SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown
  in its status) until a Frame Tweaks update catches up.
icon: {theme: transform-move}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-grab.js`), via VR
  dashboard patching (helper)
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer
  fits
undo: "`./install.sh uninstall float-grab` (or untick it in the Frame Tweaks window)"
test: {offline: true}
---
# Pick up when floating

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
"Float in World" also picks the window up, as grabbing the bar under it does, so you place it in one go; your next click (or letting go of the trigger, if you're still holding it) puts it down.

**Why on a Steam Frame:** In SteamVR, floating a window and then placing it takes two steps: press Float in World, then grab the bar under the window. This makes it one.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install float-grab
```

It brings [VR dashboard patching](../vr-dashboard/) with it if that isn't installed yet. **If
SteamVR was running when that helper was installed, restart SteamVR once** (rebooting is
easiest): SteamVR opens the local port the patch needs only when it starts.
`./install.sh status float-grab` says when it's waiting for that.

## Use
Press **Float in World** on a window as usual. The window is now **picked up**, exactly as if
you had grabbed the bar under it: it follows the controller that pressed the button.

- **Put it down** with your next click, or by letting go of the trigger if you're still holding
  the click that pressed Float in World.
- The laser is still on the button, which is now **Return to Dashboard**. While you hold the
  window, and for 1.5 seconds after, that button is ignored for it, so the click that puts the
  window down can't send it back. Press it again afterwards to dock the window.
- Untick it and it stops in the running dashboard within a few seconds. It works well with
  [Back to the previous window](../float-return/).

## How it works
One small patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/).
When a window moves from the dashboard to the world (what Float in World does), it starts the
dashboard's own drag (`startFloatingWindowMove`, what the bar under a floating window uses) for
the controller pointing at the dashboard. The drag ends the usual way, on a click. Because the
Float in World press comes from SteamVR itself rather than the page, the patch also ends the
drag when that controller's trigger moves (released, or pressed again).

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer fits
- **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-grab.js`), via VR dashboard patching (helper)
- **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown in its status) until a Frame Tweaks update catches up.
- **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
- **Undo:** `./install.sh uninstall float-grab` (or untick it in the Frame Tweaks window)
<!-- /generated:changes -->

---
Check: `./install.sh status float-grab` · Remove: `./install.sh uninstall float-grab`
