# Scroll strips

Scroll bars in desktop apps are sized for a mouse, which makes them hard to hit with a laser.
This puts **big scroll strips beside each window you float in the world**: by default a
vertical one on the **right** and a horizontal one on **top**.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
> - **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json`
> - **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs; scrolls the desktop through its Remote Desktop portal (you allow it once) and other windows with ydotool keys
> - **Undo:** `./install.sh uninstall scroll-strips` (or untick it in the installer window; settings are kept)
<!-- /generated:glance -->

- **Drag along a strip** to scroll, like dragging a scroll bar: down (or right) scrolls down
  (or right). The whole strip's length scrolls about 40 notches of a mouse wheel.
- **Tap near an end** to scroll a page that way.
- **What scrolls:**
  - **The desktop:** real mouse-wheel scrolling, of the app under the desktop's mouse pointer (where
    your laser last was in the desktop). It goes through the desktop's own Remote Desktop portal,
    so **the first time, KDE asks whether to allow remote control: allow it** (it remembers).
  - **Other windows** (Signal, the installer window, ...): the arrow keys while you drag, PgUp /
    PgDn for a tap, sent to the window you last clicked. If a text field has focus, the keys move
    its cursor instead, so click the page first.
  - Why the difference: in VR, the Steam session takes pointer input only from the lasers, so
    an injected mouse wheel never reaches a window; keyboard input does.
- **Curved windows:** the top (or bottom) strip bends with the window.
- **Settings** (the row's ⚙ button in the installer window): which side each strip is on (or off),
  and how thick they are.
- The window docked in the dashboard (the desktop, say) gets strips too, while the dashboard is open.

## How it works
A patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/), mounts a
small component in the dashboard's scene that draws two panels per window, hung from the window
panel's own edge anchors (so they follow it, docked or floating) and sized from its measured
height and shape. A drag on a strip calls `sftScroll`, a function the
helper's service registers on the dashboard page; the service scrolls the desktop through its
Remote Desktop portal (`NotifyPointerAxisDiscrete`) and other windows with [ydotool](../ydotool/)
keys. Uninstalling removes the portal's saved permission.

---
Check: `./install.sh status scroll-strips` · Remove: `./install.sh uninstall scroll-strips`
