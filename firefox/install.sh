#!/bin/bash
# Firefox (Flathub): anti-fingerprinting user.js in the default profile.
source "$(dirname "$0")/../lib/common.sh"
ROOT="$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"
[ -d "$ROOT" ] || ROOT="$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox"
[ -f "$ROOT/installs.ini" ] || die "No Firefox profile yet: start Firefox (Flathub) once, then re-run."
PROFILE=$(grep -m1 '^Default=' "$ROOT/installs.ini" | cut -d= -f2)
P="$ROOT/$PROFILE"
[ -d "$P" ] || die "Profile $P not found"

BEGIN="// >>> steam-frame-tweaks"; END="// <<< steam-frame-tweaks"
touch "$P/user.js"
# Replace our block (between markers) and keep anything else the user has in user.js.
sed -i "\|^$BEGIN|,\|^$END|d" "$P/user.js"
if [ "${1:-}" != "--remove" ]; then
    { echo "$BEGIN"; cat "$REPO_DIR/firefox/user.js"; echo "$END"; } >> "$P/user.js"
    say "Anti-fingerprinting settings written to $P/user.js"
else
    say "Removed our settings from user.js. Also reset them in about:config (prefs.js keeps old values)."
fi
pgrep -f '/app/lib/firefox/firefox ' >/dev/null && warn "Firefox is running: restart it to apply."
