#!/bin/bash
# The Open button: through the installer's own menu entry (its Steam shortcut), so the dock icon
# and SteamVR's per-app settings apply as when it's started from the library.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
setsid -f gtk-launch moonlight-xr-launcher >/dev/null 2>&1 </dev/null
