#!/bin/bash
# Prints "<installed> <latest>" for the installer window's update hint (network; quiet on failure).
cur=$(basename "$(readlink "$HOME/.local/share/framekeyboard/current" 2>/dev/null)") || exit 1
[ -n "$cur" ] && [ "$cur" != . ] || exit 1
latest=$(curl -fsSL --max-time 8 https://github.com/TaiKeid/steam-frame-full-keyboard/releases/latest/download/SHA256SUMS |
         grep -m1 -oE 'framekeyboard-[0-9.]+-aarch64' | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
[ -n "$latest" ] && echo "$cur $latest"
