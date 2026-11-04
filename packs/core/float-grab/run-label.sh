#!/bin/bash
# The Run button's label, following run.sh's switch: Turn off while it's on (also before it was
# ever pressed: on is the default), Turn on while it's turned off.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
if [ "$(dashboard_patch_switch float-grab)" = off ]; then t 'Turn on'; else t 'Turn off'; fi
echo
