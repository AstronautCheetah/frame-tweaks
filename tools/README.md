# Tools

## `restart-plasmashell`
Brings back the desktop-mode taskbar and system tray when `plasmashell` crashes. In the
Frame's nested desktop session it isn't a systemd service, so nothing restarts it
automatically. It must be launched with the session's own environment and D-Bus (taken
from `ksmserver`), which is what this script does.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `~/.local/bin/restart-plasmashell`
> - **Undo:** `./install.sh uninstall tools`
<!-- /generated:glance -->

## Credits
The nested-session environment trick is based on [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s documentation of the Frame's two sessions. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status tools` · Remove: `./install.sh uninstall tools`
