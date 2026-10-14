#!/bin/bash
# Breeze icons into hicolor, so Steam's VR "+" menu shows Konsole, System Settings, etc.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
D="$HOME/.local/share/frame-tweaks/menu-icons"
mkdir -p "$D"
install -m755 "$TWEAK_DIR/menu-icons" "$D/menu-icons"
"$D/menu-icons" install
say "Done. Steam's \"+\" menu picks them up on its own (reopen it); re-run after installing new apps."
