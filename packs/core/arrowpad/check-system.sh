#!/bin/bash
# The VR overlay loads SteamVR's own OpenVR library; typing goes through ydotoold's socket.
# shellcheck source=lib/i18n.sh
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
lib=/opt/steamvr/bin/linuxarm64/libopenvr_api.so
[ -f "$lib" ] || { t "SteamVR's %s is gone: the VR pad can't start" "$lib"; echo; exit 1; }
[ -S "/run/user/$(id -u)/.ydotool_socket" ] || { t "ydotoold's socket is missing (./install.sh status ydotool)"; echo; exit 1; }
t "SteamVR's OpenVR library and ydotoold's socket present"; echo
