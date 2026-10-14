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
  SteamVR has no setting for it (world windows always start flat), so a tiny dashboard patch
  presses the toggle for you. Restart SteamVR once after installing.
author: Frame Tweaks (approach from lhns/steam-frame-nix)
source:
  relation: idea from
  url: >-
    https://github.com/lhns/steam-frame-nix/blob/main/docs/window-curvature.md
depends: [vr-dashboard]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks
  that code each time SteamVR starts and switches itself off if it changed (shown in its status)
  until a Frame Tweaks update catches up.
icon: {theme: object-rotate-right}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/curvature.js`), via VR
  dashboard patching (helper)
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that
  changed
undo: "`./install.sh uninstall curvature`"
test: {offline: true}
---
# Curved world windows

When you **float a window in the world** (detach it from the dashboard), SteamVR shows it
flat, and there's no setting to change that: the curvature rule is hard-coded (curved in the
dashboard, theater per setting, flat in the world). This tweak presses **Toggle Curvature**
for you on every window you float, so they start curved like the dashboard.

<!-- generated:glance (dev/gen-docs.py, from each tweak's README front matter) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
> - **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/curvature.js`), via VR dashboard patching (helper)
> - **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks that code each time SteamVR starts and switches itself off if it changed (shown in its status) until a Frame Tweaks update catches up.
> - **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs
> - **Undo:** `./install.sh uninstall curvature`
<!-- /generated:glance -->

It stays your choice: toggle a window flat and it stays flat. Moving it back into the
dashboard and out again curves it again (SteamVR resets the toggle when a window is
re-docked).

```sh
./install.sh install curvature
```

**Restart SteamVR once after installing** (reboot is easiest). SteamVR opens the local port
the patch needs only when it starts; `./install.sh status curvature` says when it's waiting.

## How it works
- It's one small patch, [`patch.js`](patch.js), injected into SteamVR's dashboard by
  [VR dashboard patching](../vr-dashboard/) (installed with it; it also runs
  [Back to the previous window](../float-return/) if you install that). The patch checks windows
  a few times a second; for a world-docked window with no curvature choice yet, it calls the
  stock `ToggleCurvature()`. Nothing else in the dashboard is changed.
- Untick it in the installer window (or `./install.sh uninstall curvature`) and it stops in the
  running dashboard within a few seconds; windows keep the curvature they have.

## Credits
The approach (SteamVR's dashboard DevTools port, set only while SteamVR runs, and how the
dashboard's `curvature` component works) is from
[lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s window-curvature and
steamvr-debugger modules (Apache-2.0). No code copied: theirs makes curvature adjustable
but still starts world windows flat. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status curvature` · Remove: `./install.sh uninstall curvature`
