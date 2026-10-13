# Scroll strips

Scroll bars in desktop apps are sized for a mouse, which makes them hard to hit with a laser.
This puts **big scroll strips beside each window you float in the world**: by default a
vertical one on the **right** and a horizontal one on **top**.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches itself off if that changed
> - **Changes:** One dashboard patch (`~/.local/share/frame-tweaks/vr-dashboard/patches/scroll-strips.js`) via VR dashboard patching (helper); settings in `~/.config/frame-tweaks/scroll-strips.json`
> - **Unusual access:** Through VR dashboard patching (helper): SteamVR's dashboard DevTools port while SteamVR runs; scrolls with a mouse wheel (XTest on the Steam session's display)
> - **Undo:** `./install.sh uninstall scroll-strips` (or untick it in the installer window; settings are kept)
<!-- /generated:glance -->

- **Drag along a strip** to scroll, like dragging a scroll bar: down (or right) scrolls down
  (or right). The whole strip's length scrolls about 40 notches of a mouse wheel.
- **Tap near an end** to scroll a page that way.
- **Which window scrolls:** the one you last clicked. SteamVR gives the dashboard no way to scroll a
  particular window, so the strips use a mouse wheel, which goes to the window that
  has focus: click into a window once, then use its strips. For the desktop, it scrolls the app
  under the desktop's mouse pointer.
- **Settings** (the row's ⚙ button in the installer window): which side each strip is on (or off),
  and how thick they are.
- The window docked in the dashboard (the desktop, say) gets strips too, while the dashboard is open.

## How it works
A patch, [`patch.js`](patch.js), injected by [VR dashboard patching](../vr-dashboard/), mounts a
small component in the dashboard's scene that draws two panels per window, hung from the window
panel's own edge anchors (so they follow it, docked or floating) and sized from its measured
height and shape. A drag on a strip calls `sftScroll`, a function the
helper's service registers on the dashboard page; the service turns it into mouse-wheel notches
as mouse-wheel clicks through XTest on the Steam session's display (ydotool's virtual wheel doesn't reach app windows there).

---
Check: `./install.sh status scroll-strips` · Remove: `./install.sh uninstall scroll-strips`
