# Tools

## `restart-plasmashell`
Brings back the desktop-mode taskbar and system tray when `plasmashell` crashes. In the
Frame's nested desktop session it isn't a systemd service, so nothing restarts it
automatically. It must be launched with the session's own environment and D-Bus (taken
from `ksmserver`), which is what this script does.

## Credits
The nested-session environment trick is based on [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s documentation of the Frame's two sessions. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status tools` · Remove: `./install.sh uninstall tools`
