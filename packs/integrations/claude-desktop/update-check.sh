#!/bin/bash
# Prints "<installed> <latest>" for the installer window's update hint (network; quiet on failure).
cur=$(cat "$HOME/.local/opt/claude-desktop/.deb-version" 2>/dev/null) || exit 1
latest=$(curl -fsSL --max-time 8 https://downloads.claude.ai/claude-desktop/apt/stable/dists/stable/main/binary-arm64/Packages |
         grep ^Version: | sort -V -k2 | tail -1 | cut -d' ' -f2)
[ -n "$latest" ] && echo "$cur $latest"
