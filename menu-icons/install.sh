#!/bin/bash
# Breeze icons into hicolor, so Steam's VR "+" menu shows Konsole, System Settings, etc.
source "$(dirname "$0")/../lib/common.sh"
D="$HOME/.local/share/frame-tweaks/menu-icons"
mkdir -p "$D"
install -m755 "$REPO_DIR/menu-icons/menu-icons" "$D/menu-icons"
"$D/menu-icons" install
say "Done. Steam's \"+\" menu picks them up on its own (reopen it); re-run after installing new apps."
