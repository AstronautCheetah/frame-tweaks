#!/bin/bash
# What Recline needs from SteamOS to build and register (all on the system partition).
missing=()
[ -x /opt/steamvr/bin/linuxarm64/vrpathreg ] || missing+=("SteamVR's vrpathreg")
for t in cmake ctest c++ git; do command -v "$t" >/dev/null || missing+=("$t"); done
[ -f /usr/include/vulkan/vulkan.h ] || missing+=("the Vulkan headers")
if [ ${#missing[@]} -gt 0 ]; then
    echo "SteamOS no longer has: ${missing[*]}"
    exit 1
fi
echo "SteamVR's vrpathreg, CMake, a C++ compiler and the Vulkan headers are there"
