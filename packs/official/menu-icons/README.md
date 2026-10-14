---
title: Menu icons
emoji: 🖼️
category: System
tier: core
summary: >-
  Icons for Konsole, System Settings and other apps that show blank in Steam's VR + menu
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

Steam's VR **"+" menu** looks up app icons only in the *hicolor* theme (and `pixmaps`), so
apps whose icon only KDE's Breeze theme has show up blank: **Konsole**, **System Settings**,
and a few others (Remote Desktop/SSH viewers, Avahi, Emoji Selector, …).

<!-- generated:glance (dev/gen-docs.py, from each tweak's README front matter) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** Copies of Breeze icons in `~/.local/share/icons/hicolor`
> - **Undo:** `./install.sh uninstall menu-icons`
<!-- /generated:glance -->

This copies those icons from Breeze into `~/.local/share/icons/hicolor/scalable/apps/`, for
Konsole and System Settings always, and for every other app in the menu whose icon is missing
from hicolor but present in Breeze. Desktop mode keeps showing Breeze's icons (hicolor is only
the fallback theme), so nothing changes there.

```sh
./install.sh install menu-icons      # re-run after installing new apps
```

Steam notices on its own (it rescans when the applications folder changes); reopen the menu.
Removing the tweak deletes exactly the icons it copied (listed in
`~/.local/share/frame-tweaks/menu-icons.list`).

## Credits
The finding (Steam only resolves hicolor icons) and the fix, Breeze's `utilities-terminal` and
`preferences-system` in hicolor, are from [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix/blob/main/docs/launcher-menu.md#icon-fallbacks)
(Apache-2.0); this generalises it to any app in the menu. Icons: [KDE Breeze](https://invent.kde.org/frameworks/breeze-icons)
(LGPL-3.0), copied from your system's own Breeze theme. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status menu-icons` · Remove: `./install.sh uninstall menu-icons`
