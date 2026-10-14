---
title: Scroll strips
emoji: 📜
category: VR environment
tier: core
summary: >-
  Big scroll strips beside windows (docked or floating), easy to grab with the laser: drag to
  scroll, tap near an end to page
what: >-
  Big scroll strips beside each window, docked in the dashboard or floating (right and top by
  default), easy to grab with the laser. Press and drag away from that point to scroll, faster
  the farther you go; let go to stop. Position and thickness are set in the installer window.
why: Desktop scroll bars are sized for a mouse and hard to hit with a laser.
author: Frame Tweaks
depends: [vr-dashboard, ydotool]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks
  that code each time SteamVR starts and switches itself off if it changed (shown in its status)
  until a Frame Tweaks update catches up.
icon: {theme: transform-browse}
settings:
  file: ~/.config/frame-tweaks/scroll-strips.json
  format: json
  about: >-
    Big strips beside each window. Press one and drag away from that point to scroll (farther =
    faster; let go to stop); tap near an end to page.
  note: >-
    Changes show in VR within a few seconds. Also in VR: the gear where the strips meet.
  options:
    - key: vertical
      title: Vertical strip (scrolls up and down)
      default: right
      choices:
        - {label: Right, value: right}
        - {label: Left, value: left}
        - {label: "Off", value: "off"}
    - key: horizontal
      title: Horizontal strip (scrolls sideways)
      default: top
      choices:
        - {label: Top, value: top}
        - {label: Bottom, value: bottom}
        - {label: "Off", value: "off"}
    - key: thickness
      title: Thickness (cm)
      default: 0.04
      choices:
        - {label: "2", value: 0.02}
        - {label: "2.5", value: 0.025}
        - {label: "3", value: 0.03}
        - {label: "4", value: 0.04}
        - {label: "5", value: 0.05}
        - {label: "6", value: 0.06}
        - {label: "8", value: 0.08}
    - key: gap
      title: Gap from the window (cm)
      default: 0.015
      choices:
        - {label: "0", value: 0.0}
        - {label: "1", value: 0.01}
        - {label: "1.5", value: 0.015}
        - {label: "2", value: 0.02}
        - {label: "3", value: 0.03}
        - {label: "5", value: 0.05}
    - key: back
      title: Set back behind the window (cm)
      default: 0.03
      choices:
        - {label: "0", value: 0.0}
        - {label: "1", value: 0.01}
        - {label: "2", value: 0.02}
        - {label: "3", value: 0.03}
        - {label: "5", value: 0.05}
    - key: color
      title: Colour
      default: tint
      choices:
        - {label: Passthrough tint, value: tint}
        - {label: Red, value: 0}
        - {label: Orange, value: 0.08}
        - {label: Yellow, value: 0.15}
        - {label: Green, value: 0.33}
        - {label: Cyan, value: 0.5}
        - {label: Sky, value: 0.58}
        - {label: Blue, value: 0.67}
        - {label: Violet, value: 0.75}
        - {label: Magenta, value: 0.83}
        - {label: Pink, value: 0.92}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via
  VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json`
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs;
  scrolls with ydotool's arrow keys
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that
  changed
undo: >-
  `./install.sh uninstall scroll-strips` (or untick it in the installer window; settings are
  kept)
test:
  offline: true
  keeps: [".config/frame-tweaks/scroll-strips.json"]
---
# Scroll strips

Scroll bars in desktop apps are sized for a mouse, which makes them hard to hit with a laser.
This puts **big scroll strips beside each window you float in the world**: by default a
vertical one on the **right** and a horizontal one on **top**.

<!-- generated:glance (dev/gen-docs.py, from each tweak's README front matter) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
> - **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json`
> - **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. It checks that code each time SteamVR starts and switches itself off if it changed (shown in its status) until a Frame Tweaks update catches up.
> - **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs; scrolls with ydotool's arrow keys
> - **Undo:** `./install.sh uninstall scroll-strips` (or untick it in the installer window; settings are kept)
<!-- /generated:glance -->

- **Use a strip like a joystick:** press it, then drag away from where you pressed. The farther you
  drag, the faster it scrolls; drag back past that point to reverse; **let go to stop**. While
  you hold it, the strip lights up and shows where you pressed and where you are.
- **Tap near an end** to scroll a page that way.
- **What scrolls:** the window you last clicked (the desktop: the app you last clicked in it),
  with the arrow keys (PgUp / PgDn for a page). If a text field has focus, the keys move its
  cursor instead, so click the page or list first. Why keys: in VR the Steam session takes
  pointer input only from the lasers, so an injected mouse wheel never arrives (we tried XTest,
  ydotool and the desktop's Remote Desktop portal); keyboard input does.
- **Curved windows:** the top (or bottom) strip bends with the window.
- **The Android Mirror** is scrolled through its own helper (it sends the phone a scroll wheel),
  since the Steam session never sees that window clicked.
- **Settings in VR:** the gear where the two strips meet (by the window's top-right corner, by
  default) opens them beside the window: which side each strip is on (or off), thickness, gap
  from the window, how far it's set back, and colour (follow the passthrough's Camera Color Tint,
  or pick a hue), plus *Reset to defaults*. They apply to every window at once and are saved in
  `~/.config/frame-tweaks/scroll-strips.json` (through the VR environment helper's service).
- **Settings in the installer window** (the row's ⚙ button): side and thickness.
- The window docked in the dashboard (the desktop, say) gets strips too, while the dashboard is open.

## How it works
A patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/), mounts a
small component in the dashboard's scene that draws two panels per window, hung from the window
panel's own edge anchors (so they follow it, docked or floating) and sized from its measured
height and shape. A drag on a strip calls `sftScroll`, a function the
helper's service registers on the dashboard page; the service sends the arrow keys with
[ydotool](../ydotool/).

---
Check: `./install.sh status scroll-strips` · Remove: `./install.sh uninstall scroll-strips`
