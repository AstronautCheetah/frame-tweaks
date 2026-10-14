---
title: Menu icons
emoji: 🖼️
category: System
tier: core
summary: >-
  Icons for Konsole, System Settings and other apps that show blank in Steam's VR "+" menu
what: >-
  Icons for Konsole, System Settings and other apps that show blank in Steam's VR "+" menu.
why: >-
  Steam only looks icons up in the hicolor theme; these apps' icons exist only in KDE's Breeze
  theme.
author: Frame Tweaks (finding from lhns/steam-frame-nix)
source:
  relation: fix from
  url: >-
    https://github.com/lhns/steam-frame-nix/blob/main/docs/launcher-menu.md#icon-fallbacks
icon: {theme: preferences-desktop-icons}
changes: Copies of Breeze icons in `~/.local/share/icons/hicolor`
access: –
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall menu-icons`"
test: {offline: true}
---
# Menu icons

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Icons for Konsole, System Settings and other apps that show blank in Steam's VR "+" menu.

**Why on a Steam Frame:** Steam only looks icons up in the hicolor theme; these apps' icons exist only in KDE's Breeze theme.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install menu-icons
```

Then reopen the "+" menu. **Install it again after installing new apps**, so their icons are
added too.

## How it works
Steam's VR "+" menu looks up app icons only in the *hicolor* icon theme (and the `pixmaps`
folders). Apps whose icon only KDE's Breeze theme has, such as **Konsole** and **System
Settings**, show a blank icon there.

This copies those icons from your system's Breeze theme into
`~/.local/share/icons/hicolor/scalable/apps/`: for Konsole and System Settings, and for every
other app in the menu whose icon is in Breeze but missing from hicolor. Desktop mode keeps
showing Breeze's icons (hicolor is only the fallback theme), so nothing changes there.

Afterwards it touches the applications folder, which makes Steam rescan its "+" menu.

## Good to know
- Removing the tweak deletes exactly the icons it copied (they're listed in
  `~/.local/share/frame-tweaks/menu-icons.list`).
- Icons that hicolor already has, from the system, a Flatpak or you, are left alone.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** Copies of Breeze icons in `~/.local/share/icons/hicolor`
- **Undo:** `./install.sh uninstall menu-icons`
<!-- /generated:changes -->

## Credits
The finding (Steam only resolves hicolor icons) and the fix, Breeze's `utilities-terminal` and
`preferences-system` in hicolor, are from [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix/blob/main/docs/launcher-menu.md#icon-fallbacks)
(Apache-2.0); this generalises it to any app in the menu. Icons: [KDE Breeze](https://invent.kde.org/frameworks/breeze-icons)
(LGPL-3.0), copied from your system's own Breeze theme. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status menu-icons` · Remove: `./install.sh uninstall menu-icons`
