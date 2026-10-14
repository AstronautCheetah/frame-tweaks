#!/bin/bash
# The VR overlay loads SteamVR's own OpenVR library; typing goes through ydotoold's socket.
lib=/opt/steamvr/bin/linuxarm64/libopenvr_api.so
[ -f "$lib" ] || { echo "SteamVR's $lib is gone: the VR pad can't start"; exit 1; }
[ -S "/run/user/$(id -u)/.ydotool_socket" ] || { echo "ydotoold's socket is missing (./install.sh status ydotool)"; exit 1; }
echo "SteamVR's OpenVR library and ydotoold's socket present"
