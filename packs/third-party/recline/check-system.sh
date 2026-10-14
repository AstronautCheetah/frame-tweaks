#!/bin/bash
# What Recline needs from SteamOS to build and register (all on the system partition).
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
missing=()
[ -x /opt/steamvr/bin/linuxarm64/vrpathreg ] || missing+=("$(t "SteamVR's vrpathreg")")
for t in cmake ctest c++ git; do command -v "$t" >/dev/null || missing+=("$t"); done
[ -f /usr/include/vulkan/vulkan.h ] || missing+=("$(t 'the Vulkan headers')")
if [ ${#missing[@]} -gt 0 ]; then
    t 'SteamOS no longer has: %s' "${missing[*]}"; echo
    exit 1
fi
t "SteamVR's vrpathreg, CMake, a C++ compiler and the Vulkan headers are there"; echo
