# Tools

## `restart-plasmashell`
Brings back the desktop-mode taskbar and system tray when `plasmashell` crashes. In the
Frame's nested desktop session it isn't a systemd service, so nothing restarts it
automatically. It must be launched with the session's own environment and D-Bus (taken
from `ksmserver`), which is what this script does.
