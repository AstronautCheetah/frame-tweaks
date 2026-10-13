# Pick up when floating

Normally **Float in World** leaves the window where it was, and you then grab the bar under it
to place it. With this tweak, Float in World **picks the window up right away**, exactly as
grabbing that bar does: it follows your controller until you put it down.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
> - **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-grab.js`), via VR dashboard patching (helper)
> - **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
> - **Undo:** `./install.sh uninstall float-grab` (or untick it in the installer window)
<!-- /generated:glance -->

- **Put it down** with your next click, or by letting go of the trigger if you're still holding
  the click that pressed Float in World.
- It follows the controller that pressed the button.
- Switch it on or off by ticking **Pick up when floating** in the installer window's
  **VR windows** group. It works well with [Back to the previous window](../float-return/).
- **Restart SteamVR once** if [VR dashboard patching](../vr-dashboard/) was installed with it.

## How it works
One small patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/).
When a window's dock location changes from the dashboard to the world (what Float in World
does), it starts the dashboard's own drag (`startFloatingWindowMove`, what the bar under a
floating window uses) for the controller the dashboard says is pointing at it. The drag ends the
stock way, on a click; and because the Float in World press comes from SteamVR itself rather than
the page, the patch also ends it when that controller's trigger moves (released, or pressed again).

---
Check: `./install.sh status float-grab` · Remove: `./install.sh uninstall float-grab`
