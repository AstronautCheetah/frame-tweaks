#!/bin/bash
# Firefox (Flathub): anti-fingerprinting user.js in the default profile.
source "$(dirname "$0")/../lib/common.sh"
ROOT="$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"
[ -d "$ROOT" ] || ROOT="$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox"
[ -f "$ROOT/installs.ini" ] || die "No Firefox profile yet: start Firefox (Flathub) once, then re-run."
PROFILE=$(grep -m1 '^Default=' "$ROOT/installs.ini" | cut -d= -f2)
P="$ROOT/$PROFILE"
[ -d "$P" ] || die "Profile $P not found"

BEGIN="// >>> frame-tweaks"; END="// <<< frame-tweaks"
touch "$P/user.js"
# Replace our block (between markers) and keep anything else the user has in user.js. (Before
# 0.5 the markers said steam-frame-tweaks: those blocks go too.)
sed -i -e "\|^$BEGIN|,\|^$END|d" -e "\|^// >>> steam-frame-tweaks|,\|^// <<< steam-frame-tweaks|d" "$P/user.js"
if [ "${1:-}" != "--remove" ]; then
    { echo "$BEGIN"; cat "$REPO_DIR/firefox/user.js"; echo "$END"; } >> "$P/user.js"
    say "Anti-fingerprinting settings written to $P/user.js"
else
    say "Removed our settings from user.js."
    # Firefox copied them into prefs.js, where they'd stay: take out the same names there too.
    # (Only while it's closed: it rewrites prefs.js when it quits.)
    if pgrep -f '/app/lib/firefox/firefox ' >/dev/null; then
        warn "Firefox is running: quit it and run this again, or reset the settings in about:config."
    elif [ -f "$P/prefs.js" ]; then
        names=$(sed -n 's/^user_pref("\([^"]*\)".*/\1/p' "$REPO_DIR/firefox/user.js")
        cp "$P/prefs.js" "$P/prefs.js.frame-tweaks-bak"
        grep -vF -f <(printf 'user_pref("%s",\n' $names) "$P/prefs.js.frame-tweaks-bak" > "$P/prefs.js" || true
        say "Reset them in prefs.js too (the previous copy: prefs.js.frame-tweaks-bak)."
    fi
fi
pgrep -f '/app/lib/firefox/firefox ' >/dev/null && warn "Firefox is running: restart it to apply."
