---
title: Recline
emoji: 🛋️
category: VR environment
tier: extras
summary: Use VR lying down or reclined; one button makes your view level and forward
what: >-
  Lie back and keep playing. Press one button (or a controller shortcut) and the direction
  you're looking becomes level and forward in VR, at a chosen eye height; Reset puts everything
  back. It works for native apps on the Frame, and your hands move with you.
why: >-
  SteamVR's own recenter only turns you around; it can't tilt the world, so lying down leaves
  you looking at the ceiling. This builds [Recline-VR](https://github.com/new-waifu/Recline-VR)
  from its source and installs it for you.
author: new-waifu (Recline-VR); installer by Frame Tweaks
source:
  relation: from
  url: https://github.com/new-waifu/Recline-VR
experimental: >-
  Hooks into SteamVR's driver interface, and (for the room view) into the Frame's camera service.
  It checks those internals each time SteamVR starts and turns the affected part off if they
  changed (the room view looks tilted while reclined, or the driver doesn't load; shown in its
  status) until Recline-VR catches up.
icon: {theme: go-down-skip}
settings:
  file: ~/.config/frame-tweaks/recline.conf
  format: shell
  about: >-
    Recline's own options (rotation, eye height, the controller shortcuts) are on its panel in
    the SteamVR dashboard.
  note: >-
    Applies when you reinstall Recline, then restart SteamVR.
  options:
    - key: RECLINE_PASSTHROUGH_FIX
      title: Keep the room view aligned while reclined
      default: "on"
      choices:
        - {label: "Yes (adds a small library to the Frame's camera service)", value: "on"}
        - {label: "No (the room view looks tilted while reclined)", value: "off"}
changes: >-
  Recline-VR built from source into `~/.local/share/recline-vr`; its SteamVR driver registered
  (`~/.config/openvr/openvrpaths.vrpath`) and its dashboard panel registered to start with
  SteamVR
access: >-
  Runs inside SteamVR as a driver (sees and adjusts every tracked device's position); with the
  room-view fix, also inside the Frame's camera service
survives_updates: >-
  Yes (everything is in your home folder); after a SteamVR update it checks SteamVR's internals
  and turns off what changed. Reinstalling needs SteamOS's compiler and CMake
undo: "`./install.sh uninstall recline`, then restart SteamVR"
---
# Recline

Use VR **lying down or reclined**. [Recline-VR](https://github.com/new-waifu/Recline-VR) by
new-waifu rotates the whole tracked world, not just your heading: press **Recline recenter**
and the direction you're looking becomes level and forward, at a chosen eye height. Every
tracked device moves together, so your hands stay attached. **Reset to normal** puts it back.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder); after a SteamVR update it checks SteamVR's internals and turns off what changed. Reinstalling needs SteamOS's compiler and CMake
> - **Changes:** Recline-VR built from source into `~/.local/share/recline-vr`; its SteamVR driver registered (`~/.config/openvr/openvrpaths.vrpath`) and its dashboard panel registered to start with SteamVR
> - **🧪 Experimental:** Hooks into SteamVR's driver interface, and (for the room view) into the Frame's camera service. It checks those internals each time SteamVR starts and turns the affected part off if they changed (the room view looks tilted while reclined, or the driver doesn't load; shown in its status) until Recline-VR catches up.
> - **Unusual access:** Runs inside SteamVR as a driver (sees and adjusts every tracked device's position); with the room-view fix, also inside the Frame's camera service
> - **Undo:** `./install.sh uninstall recline`, then restart SteamVR
<!-- /generated:glance -->

```sh
./install.sh install recline
```

**Then restart SteamVR** (reboot is easiest, or `steamvr restart`): SteamVR loads drivers only
when it starts. Installing builds Recline-VR on the Frame (under a minute) and runs its tests.

## Using it
- **The Recline panel** in the SteamVR dashboard: *Recline recenter*, *Reset to normal*,
  rotation (*Full* or *Level only*) and eye height.
- **Controller shortcuts** (right controller, hold grip + trigger + bumper): **Y** reclines,
  **X** resets, **A** shows the panel. They work while a game runs. Change them from the panel
  (*Edit controller bindings*).
- **It undoes itself** when you sit up, get up, move away or take the headset off, because
  SteamVR's boundary is only right without it. The recline is never kept across SteamVR
  restarts.
- **Command line:** `~/.local/share/recline-vr/reclinectl status` (also `recenter`, `reset`).

## Good to know
- **The boundary** is drawn un-rotated, so it looks tilted while you're reclined.
- **Room view (passthrough)** stays aligned through a small library Recline-VR adds to the
  Frame's camera service. Don't want that? Set **Keep the room view aligned** to *No* in its
  settings (the ⚙ on its row, or `./install.sh settings recline`), reinstall and restart
  SteamVR; the room view then looks tilted while you're reclined.
- **Not loading?** Check that SteamVR's safe mode hasn't disabled it (SteamVR settings →
  Startup) and look for `[recline]` in `~/.local/share/Steam/logs/vrserver.txt`.

## How it's installed
- [`pin`](pin) names the exact Recline-VR commit (release v1.2.0). The installer clones it,
  checks it's that commit, builds it with SteamOS's own CMake, compiler and Vulkan headers
  in `~/.cache/frame-tweaks/recline-build`, runs its unit tests, then runs Recline-VR's own
  installer (`DEST=~/.local/share/recline-vr`). If the commit is gone upstream, it uses Frame
  Tweaks' copy of that source, checked against its SHA256.
- It refuses to build without the Vulkan headers: the panel would fall back to a way of
  drawing that has crashed SteamVR's compositor on the Frame.
- Uninstalling resets any recline, unregisters the panel and the driver, and removes
  `~/.local/share/recline-vr`. It keeps your panel options (`~/.config/recline-vr`).

## Credits
[Recline-VR](https://github.com/new-waifu/Recline-VR) is by new-waifu (MIT), with parts of the
OpenVR SDK (BSD-3-Clause, Valve) and DejaVu Sans Mono glyphs; its `LICENSE` and
`THIRD_PARTY.md` are installed with it. We also looked at
[RobcPeng/steam-frame-recline](https://github.com/RobcPeng/steam-frame-recline), a similar
project. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status recline` · Remove: `./install.sh uninstall recline`
