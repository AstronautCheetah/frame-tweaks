# Scroll strips

Scroll bars in desktop apps are sized for a mouse, which makes them hard to hit with a laser.
This puts **big scroll strips beside each window you float in the world**: by default a
vertical one on the **right** and a horizontal one on **top**.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
> - **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json`
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
  `~/.config/frame-tweaks/scroll-strips.json` (through the VR windows helper's service).
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
