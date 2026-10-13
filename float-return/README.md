# Back to the previous window

When you **float the window the dashboard is showing** out into the world, SteamVR leaves an
empty space in the dashboard where it was. With this tweak, after **2.5 seconds** the dashboard
shows the window you had before, the same as clicking that window's button in the dashboard bar.

The same when the window the dashboard shows is **closed** (a finished or cancelled
[Screen snip](../snip/), say): instead of falling back to Steam, the dashboard goes back to the
window before it (Steam may show for a moment first).

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
> - **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/float-return.js`), via VR dashboard patching (helper)
> - **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
> - **Undo:** `./install.sh uninstall float-return` (or untick it in the installer window)
<!-- /generated:glance -->

- Switch it on or off by ticking **Back to the previous window** in the installer window's
  **VR windows** group (it stops in the running dashboard within a few seconds).
- It only acts right after a float: if you dock the window again within that time, or pick
  another window yourself, it does nothing. Floating a window you opened from a world window,
  or one with nothing shown before it, also leaves the dashboard as it is.
- **Restart SteamVR once** if [VR dashboard patching](../vr-dashboard/) was installed with it.

## How it works
One small patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/).
It keeps a short list of the windows the dashboard showed; when the shown window's dock
location changes from the dashboard to the world, it waits 2.5 s and calls the dashboard's own
`switchToFrameInternal()` with the window before it that is still docked in the dashboard.

---
Check: `./install.sh status float-return` · Remove: `./install.sh uninstall float-return`
