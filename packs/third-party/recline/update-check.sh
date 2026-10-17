#!/bin/bash
# Prints "<installed> <newest>" for the installer window's update hint (↻ then installs it): the
# version Recline-VR's installer wrote (git describe: v1.3.0, or v1.3.0+3.14d0169 past it), and its
# newest release, from where GitHub's "latest release" link leads (no API: no rate limit).
cur=$(cat "$HOME/.local/share/recline-vr/VERSION" 2>/dev/null) || exit 1
cur=${cur%-dirty} cur=${cur#v}
case $cur in ""|unknown*) exit 1 ;; esac     # (built without its git history: nothing to compare)
latest=$(curl -fsI --max-time 8 https://github.com/new-waifu/Recline-VR/releases/latest |
         sed -n 's|^[Ll]ocation: .*/releases/tag/v\{0,1\}\([^[:space:]]*\).*|\1|p' | head -1)
[ -n "$latest" ] && echo "$cur $latest"
