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
  the farther you go; let go to stop. Set them up in the Frame Tweaks window or from a gear
  beside each window in VR.
why: >-
  In VR you point with a laser, and the scroll bars in desktop apps are sized for a mouse: thin
  and hard to hit.
author: Frame Tweaks
depends: [vr-dashboard, ydotool]
experimental: >-
  Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time
  SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown
  in its status) until a Frame Tweaks update catches up.
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
    - key: haptics
      title: Haptics (a tick on the controller as you scroll)
      checkbox: true
      default: true
      choices:
        - {label: "On", value: true}
        - {label: "Off", value: false}
changes: >-
  One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via
  VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json`
access: >-
  Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs;
  scrolls with ydotool's arrow keys
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer
  fits
undo: >-
  `./install.sh uninstall scroll-strips` (or untick it in the Frame Tweaks window; settings are
  kept)
test:
  offline: true
  keeps: [".config/frame-tweaks/scroll-strips.json"]
---
# Scroll strips

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Big scroll strips beside each window, docked in the dashboard or floating (right and top by default), easy to grab with the laser. Press and drag away from that point to scroll, faster the farther you go; let go to stop. Set them up in the Frame Tweaks window or from a gear beside each window in VR.

**Why on a Steam Frame:** In VR you point with a laser, and the scroll bars in desktop apps are sized for a mouse: thin and hard to hit.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install scroll-strips
```

It brings [VR dashboard patching](../vr-dashboard/) and [ydotool](../ydotool/) (which sends the
scroll keys) with it if they aren't installed yet. **If SteamVR was running when VR dashboard
patching was installed, restart SteamVR once** (rebooting is easiest): SteamVR opens the local
port the patch needs only when it starts. `./install.sh status scroll-strips` says when it's
waiting for that.

## Use
Every window floating in the world gets a vertical strip on its **right** and a horizontal one
on **top** (you can change both). So does the window shown in the dashboard, while the
dashboard is open.

- **Use a strip like a joystick:** press it, then drag away from where you pressed. The farther
  you drag, the faster it scrolls; drag back past that point to reverse; **let go to stop**.
  While you hold it, the strip lights up and shows where you pressed and where you are.
- **Tap near an end** to scroll a page that way.
- **What scrolls:** the window you last clicked (for the desktop, the app you last clicked in
  it). The strips scroll with the arrow keys (Page Up / Page Down for a page), so if a text
  field has focus, the keys move its cursor instead: click the page or list first.
- **Curved windows:** the top (or bottom) strip bends with the window.
- **Android Mirror:** with [Android Mirror](../adb-scrcpy/) running, its strips scroll the
  phone itself, as a scroll wheel would.

## Settings
Two places, same settings, saved in `~/.config/frame-tweaks/scroll-strips.json`. They apply to
every window at once.

- **In VR:** the gear where the two strips meet (by the window's top-right corner, by default)
  opens a settings panel beside the window. Changes show at once; *Reset to defaults* puts
  everything back.
- **In the Frame Tweaks window:** the ⚙ on its row (or `./install.sh settings scroll-strips`).
  Changes show in VR within a few seconds.

| Setting | Choices | Default |
|---|---|---|
| Vertical strip | right, left, off | right |
| Horizontal strip | top, bottom, off | top |
| Thickness | 2 to 8 cm | 4 cm |
| Gap from the window | 0 to 5 cm | 1.5 cm |
| Set back behind the window | 0 to 5 cm | 3 cm |
| Colour | the passthrough's Camera Color Tint, or one of ten hues | the tint |
| Haptics | a tick box: a tick on the controller when the laser reaches a strip, as it scrolls and on a page | on |

Setting the strips back a little keeps SteamVR's own buttons by the window's edge drawn in
front of them. Uninstalling keeps your settings.

## How it works
A patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/), draws
two panels per window in the dashboard's 3D scene. They hang from the window's own edges, so
they follow it, docked or floating, and are sized from its measured height and shape. A drag on
a strip asks the helper's service to send arrow keys with [ydotool](../ydotool/).

Why keys and not a scroll wheel: in VR the Steam session takes pointer input only from the
lasers, so a scroll wheel sent by another program doesn't reach the app. Keyboard input does.
For Android Mirror the scroll goes through the mirror's own touch helper instead, because the
Steam session never sees that window clicked.

## Good to know
- If the laser stays completely still on a held strip for 3 seconds, the strip stops scrolling,
  as if you had let go (so a lost release can't leave it scrolling).

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and stays off if it no longer fits
- **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json`
- **🧪 Experimental:** Relies on SteamVR's internal dashboard code, which Valve can change in any update. Each time SteamVR starts, it's checked against that code and left off if a piece it needs is gone (shown in its status) until a Frame Tweaks update catches up.
- **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs; scrolls with ydotool's arrow keys
- **Undo:** `./install.sh uninstall scroll-strips` (or untick it in the Frame Tweaks window; settings are kept)
<!-- /generated:changes -->

---
Check: `./install.sh status scroll-strips` · Remove: `./install.sh uninstall scroll-strips`
