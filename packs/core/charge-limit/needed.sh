#!/bin/bash
# Withdrawn for new installs: a SteamOS charger bug (SteamOS #2879) stops some Frames taking
# power from USB while plugged in, and this tweak's pause and resume every few minutes may set it
# off (its README). Exit 1 with why, so the window hides it and ./install.sh install skips it,
# unless it's installed already: then it stays listed, and updates install it again.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
echo "$(t "withdrawn for new installs while a SteamOS charger bug can leave a Frame unable to charge (SteamOS #2879)")"
exit 1
