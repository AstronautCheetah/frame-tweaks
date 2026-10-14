#!/bin/bash
# Firefox (Flathub): anti-fingerprinting user.js in the default profile.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ROOT="$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"
[ -d "$ROOT" ] || ROOT="$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox"
[ -f "$ROOT/installs.ini" ] || die "$(t 'No Firefox profile yet: start Firefox (Flathub) once, then re-run.')"
PROFILE=$(grep -m1 '^Default=' "$ROOT/installs.ini" | cut -d= -f2)
P="$ROOT/$PROFILE"
[ -d "$P" ] || die "$(t 'Profile %s not found' "$P")"

BEGIN="// >>> frame-tweaks"; END="// <<< frame-tweaks"
touch "$P/user.js"
# Replace our block (between markers) and keep anything else the user has in user.js. (Before
# 0.5 the markers said steam-frame-tweaks: those blocks go too.)
sed -i -e "\|^$BEGIN|,\|^$END|d" -e "\|^// >>> steam-frame-tweaks|,\|^// <<< steam-frame-tweaks|d" "$P/user.js"
if [ "${1:-}" != "--remove" ]; then
    { echo "$BEGIN"; cat "$TWEAK_DIR/user.js"; echo "$END"; } >> "$P/user.js"
    say "$(t 'Anti-fingerprinting settings written to %s' "$P/user.js")"
else
    say "$(t 'Removed our settings from user.js.')"
    # Firefox copied them into prefs.js, where they'd stay: take out the same names there too.
    # (Only while it's closed: it rewrites prefs.js when it quits.)
    if pgrep -f '/app/lib/firefox/firefox ' >/dev/null; then
        warn "Firefox is running: quit it and run this again, or reset the settings in about:config."
    elif [ -f "$P/prefs.js" ]; then
        names=$(sed -n 's/^user_pref("\([^"]*\)".*/\1/p' "$TWEAK_DIR/user.js")
        cp "$P/prefs.js" "$P/prefs.js.frame-tweaks-bak"
        grep -vF -f <(printf 'user_pref("%s",\n' $names) "$P/prefs.js.frame-tweaks-bak" > "$P/prefs.js" || true
        say "$(t 'Reset them in prefs.js too (the previous copy: prefs.js.frame-tweaks-bak).')"
    fi
fi
if pgrep -f '/app/lib/firefox/firefox ' >/dev/null; then warn "$(t 'Firefox is running: restart it to apply.')"; fi
