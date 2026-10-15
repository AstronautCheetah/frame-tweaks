#!/bin/bash
# Recording, the silence check and the clipboard need these system tools.
# shellcheck source=lib/i18n.sh
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/i18n.sh"
miss=()
for b in pw-record pw-play ffmpeg; do command -v "$b" >/dev/null || miss+=("$b"); done
[ ${#miss[@]} -eq 0 ] || { t 'missing: %s' "${miss[*]}"; echo; exit 1; }
t 'PipeWire tools and ffmpeg present'; echo
