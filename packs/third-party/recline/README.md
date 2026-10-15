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
  you looking at the ceiling. Linked: [Recline-VR](https://github.com/new-waifu/Recline-VR)
  builds and installs itself on the Frame, the way its README describes.
author: new-waifu (Recline-VR)
source:
  relation: from
  url: https://github.com/new-waifu/Recline-VR
experimental: >-
  Hooks into SteamVR's driver interface, and (for the room view) into the Frame's camera service.
  Recline-VR checks those internals each time SteamVR starts and turns the affected part off if
  they changed (the driver doesn't load, or the room view looks tilted while reclined; its panel
  and `reclinectl status` say so) until Recline-VR catches up.
icon: {theme: go-down-skip}
link:
  install: if [ -d ~/Recline-VR/.git ]; then git -C ~/Recline-VR pull --ff-only; else git clone https://github.com/new-waifu/Recline-VR.git ~/Recline-VR; fi && ~/Recline-VR/install.sh
  uninstall: ~/.local/share/recline-vr/uninstall.sh && rm -rf ~/.local/share/recline-vr ~/Recline-VR
  installed: ~/.local/share/recline-vr/recline_overlay
  restart: steamvr
  readme: https://github.com/new-waifu/Recline-VR#readme
changes: >-
  Whatever Recline-VR's own installer sets up (its README lists it): its source in
  `~/Recline-VR`, built and installed into `~/.local/share/recline-vr`; its SteamVR driver
  registered (`~/.config/openvr/openvrpaths.vrpath`) and its dashboard panel registered to start
  with SteamVR
access: >-
  Runs inside SteamVR as a driver (sees and adjusts every tracked device's position), and inside
  the Frame's camera service for the room view
survives_updates: >-
  Yes (everything is in your home folder); after a SteamVR update Recline-VR checks SteamVR's
  internals and turns off what changed. Updating needs SteamOS's compiler, CMake and git
undo: "Uncheck it, or `./install.sh uninstall recline`: Recline-VR's own uninstaller; then restart SteamVR"
---
# Recline

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Lie back and keep playing. Press one button (or a controller shortcut) and the direction you're looking becomes level and forward in VR, at a chosen eye height; Reset puts everything back. It works for native apps on the Frame, and your hands move with you.

**Why on a Steam Frame:** SteamVR's own recenter only turns you around; it can't tilt the world, so lying down leaves you looking at the ceiling. Linked: [Recline-VR](https://github.com/new-waifu/Recline-VR) builds and installs itself on the Frame, the way its README describes.
<!-- /generated:intro -->

A **link**: Frame Tweaks runs Recline-VR's own commands, as its
[README](https://github.com/new-waifu/Recline-VR#readme) gives them, in the terminal it opens for
installs, and doesn't pin, check or change what they install.

- **Install** (tick it): clones Recline-VR into `~/Recline-VR` and runs its `install.sh`, which
  builds it on the Frame, runs its tests and installs it into `~/.local/share/recline-vr` (under
  a minute). **Then restart SteamVR**: SteamVR loads drivers only when it starts. Until then its
  row in the Frame Tweaks window says so and offers **⟳ Restart SteamVR** (every open app
  closes); rebooting works too.
- **Update:** ↻ on its row pulls the latest Recline-VR and runs its installer again; then restart
  SteamVR. Frame Tweaks' own updates leave it alone.
- **Uninstall** (untick it): runs `~/.local/share/recline-vr/uninstall.sh`, which unregisters its
  panel and driver, then removes `~/.local/share/recline-vr` and `~/Recline-VR`. **Then restart
  SteamVR** to unload the driver: until then its row offers **⟳ Restart SteamVR**. Your panel
  options stay in `~/.config/recline-vr`.

## Use
- **The Recline panel** in the SteamVR dashboard: *Recline recenter*, *Reset to normal*,
  rotation (*Full* or *Level only*) and eye height.
- **Controller shortcuts** (right controller, hold grip + trigger + bumper): **Y** reclines,
  **X** resets, **A** shows the panel. They work while a game runs, but not while the
  dashboard is open. Change them from the panel (*Edit controller bindings*).
- **It undoes itself** when you sit up, get up, move away or take the headset off, because
  SteamVR's boundary is only right without it. The recline is never kept across SteamVR
  restarts.
- **Command line:** `~/.local/share/recline-vr/reclinectl status` (also `recenter`, `reset`).

Recline-VR's [README](https://github.com/new-waifu/Recline-VR#readme) describes every panel option.

## Good to know
- **The boundary** is drawn un-rotated, so it looks tilted while you're reclined.
- **The room view** stays level through a small library Recline-VR adds to the Frame's camera
  service. If it can't load, the room view looks tilted while reclined
  (`~/.local/share/recline-vr/xrshim.log` says why).
- **Not loading?** Check that SteamVR's safe mode hasn't turned it off (SteamVR settings →
  Startup) and look for `[recline]` in `~/.local/share/Steam/logs/vrserver.txt`.
- **Install and uninstall while SteamVR runs:** its panel can only be registered and
  unregistered then.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder); after a SteamVR update Recline-VR checks SteamVR's internals and turns off what changed. Updating needs SteamOS's compiler, CMake and git
- **Changes:** Whatever Recline-VR's own installer sets up (its README lists it): its source in `~/Recline-VR`, built and installed into `~/.local/share/recline-vr`; its SteamVR driver registered (`~/.config/openvr/openvrpaths.vrpath`) and its dashboard panel registered to start with SteamVR
- **🧪 Experimental:** Hooks into SteamVR's driver interface, and (for the room view) into the Frame's camera service. Recline-VR checks those internals each time SteamVR starts and turns the affected part off if they changed (the driver doesn't load, or the room view looks tilted while reclined; its panel and `reclinectl status` say so) until Recline-VR catches up.
- **Unusual access:** Runs inside SteamVR as a driver (sees and adjusts every tracked device's position), and inside the Frame's camera service for the room view
- **Undo:** Uncheck it, or `./install.sh uninstall recline`: Recline-VR's own uninstaller; then restart SteamVR
<!-- /generated:changes -->

## Credits
[Recline-VR](https://github.com/new-waifu/Recline-VR) is by new-waifu (MIT), with parts of the
OpenVR SDK (BSD-3-Clause, Valve) and DejaVu Sans Mono glyphs; its `LICENSE` and
`THIRD_PARTY.md` are installed with it. We also looked at
[RobcPeng/steam-frame-recline](https://github.com/RobcPeng/steam-frame-recline), a similar
project. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status recline` · Remove: `./install.sh uninstall recline`
