#!/bin/bash
# Recording, the silence check and the clipboard need these system tools.
miss=()
for b in pw-record pw-play ffmpeg; do command -v "$b" >/dev/null || miss+=("$b"); done
[ ${#miss[@]} -eq 0 ] || { echo "missing: ${miss[*]}"; exit 1; }
echo "PipeWire tools and ffmpeg present"
