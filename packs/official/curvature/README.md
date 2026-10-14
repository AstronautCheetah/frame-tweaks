---
title: Curved world windows
emoji: 🌀
category: VR environment
tier: core
summary: >-
  Windows you float into the world start curved, like the dashboard (Toggle Curvature still
  works)
what: >-
  Windows you float into the world start curved, like the dashboard; Toggle Curvature still
  works.
why: >-
  On the Frame, windows you float out of the dashboard always start flat, and SteamVR has no
  setting to change that. This presses its Toggle Curvature button for you on each one.
author: Frame Tweaks (approach from lhns/steam-frame-nix)
source:
  relation: idea from
  url: >-
    https://github.com/lhns/steam-frame-nix/blob/main/docs/window-curvature.md
depends: [vr-dashboard]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time
  SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown
  in its status) until a Frame Tweaks update catches up.
icon: {theme: object-rotate-right}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/curvature.js`), via VR
  dashboard patching (helper)
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer
  fits
undo: "`./install.sh uninstall curvature` (or untick it in the Frame Tweaks window)"
test: {offline: true}
---
# Curved world windows

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Windows you float into the world start curved, like the dashboard; Toggle Curvature still works.

**Why on a Steam Frame:** On the Frame, windows you float out of the dashboard always start flat, and SteamVR has no setting to change that. This presses its Toggle Curvature button for you on each one.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install curvature
```

It brings [VR dashboard patching](../vr-dashboard/) with it if that isn't installed yet. **If
SteamVR was running when that helper was installed, restart SteamVR once** (rebooting is
easiest): SteamVR opens the local port the patch needs only when it starts.
`./install.sh status curvature` says when it's waiting for that.

## Use
Nothing to do: **float a window in the world** (move it out of the dashboard) and it starts
curved.

- It stays your choice: press **Toggle Curvature** to make a window flat and it stays flat.
- Moving a window back into the dashboard and out again curves it again (SteamVR forgets the
  toggle when a window is docked).
- Untick it and it stops in the running dashboard within a few seconds; windows keep the
  curvature they have.

## How it works
SteamVR's rule for curving windows is fixed in its dashboard code: curved in the dashboard,
theater mode as set, flat in the world, unless you've pressed Toggle Curvature. This tweak is
one small patch, [`patch.js`](patch.js), injected into the dashboard by
[VR dashboard patching](../vr-dashboard/). A few times a second it looks for a window in the
world that is flat and that you haven't toggled yet, and calls the dashboard's own
`ToggleCurvature()` on it. Nothing else in the dashboard is changed.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer fits
- **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/curvature.js`), via VR dashboard patching (helper)
- **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown in its status) until a Frame Tweaks update catches up.
- **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
- **Undo:** `./install.sh uninstall curvature` (or untick it in the Frame Tweaks window)
<!-- /generated:changes -->

## Credits
The approach (SteamVR's dashboard DevTools port, set only while SteamVR runs, and how the
dashboard's `curvature` component works) is from
[lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s window-curvature and
steamvr-debugger modules (Apache-2.0). No code copied: theirs makes curvature adjustable
but still starts world windows flat. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status curvature` · Remove: `./install.sh uninstall curvature`
