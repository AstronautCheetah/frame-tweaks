#!/bin/bash
# The Run button's label, following run.sh's switch: Turn off while it's on (also before it was
# ever pressed: on is the default), Turn on while it's turned off.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# (⏻, the power symbol: the window shows a label starting with a symbol as it is, not after ▶.)
if [ "$(dashboard_patch_switch float-grab)" = off ]; then printf '⏻ %s\n' "$(t 'Turn on')"; else printf '⏻ %s\n' "$(t 'Turn off')"; fi
