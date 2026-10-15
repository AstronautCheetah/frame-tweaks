#!/bin/bash
# Prints "<installed> <newest>" for the installer window's update hint (↻ then installs it): the
# newest release's version, from the name of its archive in its SHA256SUMS.
cur=$(basename "$(readlink "$HOME/.local/share/framekeyboard/current" 2>/dev/null)") || exit 1
[ -n "$cur" ] && [ "$cur" != . ] || exit 1
latest=$(curl -fsSL --max-time 8 https://github.com/TaiKeid/steam-frame-full-keyboard/releases/latest/download/SHA256SUMS |
         sed -n 's/.*framekeyboard-\(.*\)-aarch64\.tar\.gz$/\1/p' | head -1)
[ -n "$latest" ] && echo "$cur $latest"
