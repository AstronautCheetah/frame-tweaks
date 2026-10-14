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
upstream_readme: https://raw.githubusercontent.com/new-waifu/Recline-VR/ee7d4b3cf1ce49904117bbcf623680b2171d3d83/README.md
---
# Recline

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Lie back and keep playing. Press one button (or a controller shortcut) and the direction you're looking becomes level and forward in VR, at a chosen eye height; Reset puts everything back. It works for native apps on the Frame, and your hands move with you.

**Why on a Steam Frame:** SteamVR's own recenter only turns you around; it can't tilt the world, so lying down leaves you looking at the ceiling. This builds [Recline-VR](https://github.com/new-waifu/Recline-VR) from its source and installs it for you.
<!-- /generated:intro -->

Use VR **lying down or reclined**. [Recline-VR](https://github.com/new-waifu/Recline-VR) by
new-waifu rotates the whole tracked world, not just your heading: press **Recline recenter**
and the direction you're looking becomes level and forward, at a chosen eye height. Every
tracked device moves together, so your hands stay attached. **Reset to normal** puts it back.


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

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder); after a SteamVR update it checks SteamVR's internals and turns off what changed. Reinstalling needs SteamOS's compiler and CMake
- **Changes:** Recline-VR built from source into `~/.local/share/recline-vr`; its SteamVR driver registered (`~/.config/openvr/openvrpaths.vrpath`) and its dashboard panel registered to start with SteamVR
- **🧪 Experimental:** Hooks into SteamVR's driver interface, and (for the room view) into the Frame's camera service. It checks those internals each time SteamVR starts and turns the affected part off if they changed (the room view looks tilted while reclined, or the driver doesn't load; shown in its status) until Recline-VR catches up.
- **Unusual access:** Runs inside SteamVR as a driver (sees and adjusts every tracked device's position); with the room-view fix, also inside the Frame's camera service
- **Undo:** `./install.sh uninstall recline`, then restart SteamVR
<!-- /generated:changes -->

## Credits
[Recline-VR](https://github.com/new-waifu/Recline-VR) is by new-waifu (MIT), with parts of the
OpenVR SDK (BSD-3-Clause, Valve) and DejaVu Sans Mono glyphs; its `LICENSE` and
`THIRD_PARTY.md` are installed with it. We also looked at
[RobcPeng/steam-frame-recline](https://github.com/RobcPeng/steam-frame-recline), a similar
project. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status recline` · Remove: `./install.sh uninstall recline`

<!-- generated:upstream (dev/gen-docs.py, from upstream.md) -->
---

*The rest of this page is [new-waifu/Recline-VR](https://github.com/new-waifu/Recline-VR)'s own README at `ee7d4b3cf1ce`, as its author wrote it (only links and heading levels adjusted), included for its instructions and credits. Everything above is Frame Tweaks'.*

## Recline VR

*Lie back and keep playing. Full pitch/roll recentering for SteamVR, built for the
Steam Frame.*

Use VR lying down or reclined. Press one button and the direction you are looking
becomes level and forward in VR, at a chosen eye height. It works for native apps on
the Frame (OpenVR and OpenXR, standing and seated), and every tracked device moves
together, so your hands stay attached. Reset puts everything back.

SteamVR's own recenter can only turn you around (yaw), not tilt the world. Recline
VR rotates the whole tracked world instead; [docs/DESIGN.md](https://github.com/new-waifu/Recline-VR/blob/ee7d4b3cf1ce49904117bbcf623680b2171d3d83/docs/DESIGN.md)
explains how and why.

| Part | Path | What |
|---|---|---|
| `driver_recline.so` | `driver/` | SteamVR driver (adds no devices) that applies the recline rotation to every tracked device's pose. |
| `librecline_xrshim.so` | `xrshim/` | Loaded into the Frame's `XRService` only (never into games); corrects the passthrough mesh and camera poses for the recline rotation. |
| `recline_overlay` | `overlay/` | Dashboard panel, controller actions and haptics; `--register` / `--unregister` for SteamVR. |
| `reclinectl` | `cli/` | Command-line client: status, recenter, reset, diagnostics. |
| shared code | `common/` | `/recline_v1` shared-memory protocol, transform and recenter math. |

### Using it

**Dashboard panel ("Recline"):**

- **Recline recenter** makes your current view level and forward. **Reset to normal**
  undoes it.
- **Rotation:** *Full* also turns you to face the play area's forward direction;
  *Level only* keeps the direction you're facing and just straightens the horizon
  (on your back, you end up facing your feet).
- **Position:** *Target height* puts your eyes at the chosen height above the floor
  (presets *Sitting 1.20* and *Standing 1.50*, ±5 cm steps); *Keep position* leaves
  your position alone.
- **Also reset seated zero pose after recenter / reset** (on by default) keeps
  seated-space games, sims and many OpenXR titles centred on you.
- **Edit controller bindings** opens SteamVR's binding editor directly on this app.
- **Show in dashboard** (on by default): untick it to remove the Recline icon from
  the SteamVR dashboard once the dashboard closes; the controller shortcuts keep
  working. To open the panel again, bind *Show the Recline panel* (unbound by
  default) or run `reclinectl panel show`.
  working. To open the panel again, use the *Show the Recline panel* shortcut
  (below) or run `reclinectl panel show`. If that shortcut is unbound, the panel
  warns first and hides on a second click.
- **Recline on SteamVR's recenter when tilted over** (off by default): SteamVR's own
  recenter (system button or menu) then also reclines you when your view is tilted
  more than the set angle (35° by default, 20–75°; pitch and roll both count, so
  lying on your back, side or front all work), and undoes the recline when you
  recenter sitting or standing up. A brief "Reclined" or "Back to normal" in view
  says which happened. *Recline recenter* still works at any angle.
- The status area shows whether the driver is loaded, the current rotation, and
  warnings (another tool hooking poses, boundary limitations).

"Level" means what you see straight through the lenses. On the Frame that is about
14° below the headset's nominal forward axis; the offset is read from SteamVR, so
other headsets work too.

**Controller shortcuts** (default bindings, changeable via the button above). On the
right controller, hold **grip + trigger + bumper** and press **Y** to recenter,
**X** to reset, or **A** to show the panel. They are plain SteamVR chords that work
while a game is running (but not while the dashboard is open).
Defaults are deliberately finger-twisting combinations that normal gameplay won't
produce.

**Safety:** the recline is undone automatically when you sit up, get up, move
away or take the headset off, because SteamVR's boundary is only right without
it. A short "Back to normal" in view tells you it happened.

**Command line** (`~/.local/share/recline-vr/reclinectl`):

    reclinectl status                      # driver loaded? hook? current rotation, conflicts
    reclinectl recenter [--level-only] [--keep-position] [--height M] [--no-seated-reset]
    reclinectl reset [--no-seated-reset]
    reclinectl set <yaw> <pitch> <roll> <x> <y> <z>   # explicit rotation (deg, m), testing
    reclinectl poses                       # device poses per tracking space + display geometry
    reclinectl bindings                    # open the binding editor in the headset
    reclinectl panel show|hide             # Recline icon in the SteamVR dashboard
    reclinectl setting get|set|remove <section> <key> [value]  # SteamVR settings, for experiments

### Install / uninstall

On the Frame (it ships with CMake and a compiler), with SteamVR running:

    git clone https://github.com/new-waifu/Recline-VR.git
    cd Recline-VR
    ./install.sh        # builds, runs the unit tests, installs to ~/.local/share/recline-vr
    steamvr restart

Everything goes into your home directory; nothing in `/opt` is touched. To update,
`git pull` and run `./install.sh` again, then restart SteamVR the same way.

Uninstall (SteamVR running):

    ~/.local/share/recline-vr/uninstall.sh   # unregisters overlay and driver
    steamvr restart
    rm -rf ~/.local/share/recline-vr         # optionally also /dev/shm/recline_v1

### Build

The OpenVR SDK is vendored in `third_party/openvr`; the overlay and CLI link its
`openvr_api` loader statically. By hand:

    cmake -S . -B build && cmake --build build -j && ctest --test-dir build
    build/stage/install.sh      # installs the staged layout

The overlay uses Vulkan when its headers are available at build time and falls back
to `SetOverlayRaw` otherwise.

The version (next to the panel title, `reclinectl --version`, and the driver's line
in `vrserver.txt`) comes from `git describe`: `v1.1.0` for a tagged commit,
`v1.1.0+3.14d0169` three commits later, `-dirty` with uncommitted changes.
`-DRECLINE_VERSION=...` overrides it.

### Settings

Driver (`recline/resources/settings/default.vrsettings`, section `driver_recline`):

- `loadPriority` (100000): load before other drivers (including Space Calibrator)
  so their pose hooks wrap ours.
- `debugPitchDeg` (0): apply a fixed pitch about the head at startup, for testing
  without the overlay.
- `downstreamCheck` (true): periodically check that nothing modifies poses after us.

Overlay options are saved in `~/.config/recline-vr/overlay.conf`. The recline
rotation itself is never saved: it is always reset when SteamVR restarts.

### Troubleshooting

The driver logs to `~/.local/share/Steam/logs/vrserver.txt` with prefix `[recline]`:

- `hook installed; chained to …`: working. `hook refused: …` explains why not.
- `GetRawTrackedDevicePoses returns post-world-from-driver poses …`: the conflict
  check is usable; with `… driver-space poses` it disables itself.
- `another pose hook wraps ours …`: another tool (e.g. a calibrator) hooks poses
  and runs before recline, which is the right order for a calibrator.
  `conflict: … modified after our hook …`: something changes poses after recline;
  see docs/DESIGN.md.

If the overlay says the driver isn't loaded, check that SteamVR's safe mode hasn't
disabled it (SteamVR settings, Startup) and that `vrpathreg show` lists the driver.

### Known limitations

- Passthrough (3D and 2D room view) relies on the XRService shim. If it can't load
  or its safety checks fail, passthrough is misaligned while reclined (see
  `~/.local/share/recline-vr/xrshim.log`).
- The boundary is drawn un-rotated and looks tilted while reclined, so Recline
  resets itself as soon as you get up, move away or take the headset off (see
  docs/DESIGN.md). While you lie still, your hands may not trigger the boundary
  where you'd expect.
- A recenter invalidates PC-side tracker calibration (e.g. Space Calibrator) while
  streaming.

### License

MIT; see [LICENSE](https://github.com/new-waifu/Recline-VR/blob/ee7d4b3cf1ce49904117bbcf623680b2171d3d83/LICENSE). Bundled third-party material keeps its own license
(see [THIRD_PARTY.md](https://github.com/new-waifu/Recline-VR/blob/ee7d4b3cf1ce49904117bbcf623680b2171d3d83/THIRD_PARTY.md)).
<!-- /generated:upstream -->
