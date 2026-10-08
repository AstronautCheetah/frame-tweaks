#!/bin/bash
# Prints "<installed> <latest>" for the installer window's update hint (network; quiet on failure).
cur=$(cat "$HOME/.local/lib/whisper-frame/VERSION" 2>/dev/null) || exit 1
tag=$(curl -fsSL --max-time 8 https://api.github.com/repos/groffta/whisper-frame/releases/latest |
      sed -n 's/.*"tag_name": *"v\{0,1\}\([^"]*\)".*/\1/p' | sed -n 1p)
[ -n "$tag" ] && echo "$cur $tag"
