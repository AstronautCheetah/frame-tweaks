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
# Firefox copies our settings into prefs.js (as user_pref("NAME", ...) lines). Those of them you
# had set yourself before the first install (HTTPS-only mode, say) are recorded in SAVED as they
# were, and put back when the tweak is removed. (Recorded once, while our block isn't in user.js
# yet: once it is, prefs.js has Firefox's copies of ours. Installed before this was recorded,
# removing resets them all.)
names=$(sed -n 's/^user_pref("\([^"]*\)".*/\1/p' "$TWEAK_DIR/user.js")
ours() { printf 'user_pref("%s",\n' $names; }        # (the start of their lines)
SAVED="$BACKUPS/firefox/${P#"$HOME"/}/prefs.js.before"
installed=; grep -qE '^// >>> (steam-)?frame-tweaks' "$P/user.js" && installed=1
# Replace our block (between markers) and keep anything else the user has in user.js. (Before
# 0.5 the markers said steam-frame-tweaks: those blocks go too.) A start marker without its end
# would have sed delete everything after it, the user's own lines too: stop instead.
for m in frame-tweaks steam-frame-tweaks; do
    awk -v b="// >>> $m" -v e="// <<< $m" 'index($0, b) == 1 { if (open) exit 1; open = 1 }
        index($0, e) == 1 { open = 0 } END { exit open }' "$P/user.js" ||
        die "$(t "%s has a '%s' line without its '%s' line: fix that by hand, then run this again." "$P/user.js" "// >>> $m" "// <<< $m")"
done
sed -i -e "\|^$BEGIN|,\|^$END|d" -e "\|^// >>> steam-frame-tweaks|,\|^// <<< steam-frame-tweaks|d" "$P/user.js"
if [ "${1:-}" != "--remove" ]; then
    if [ -z "$installed" ] && [ ! -e "$SAVED" ]; then
        mkdir -p "${SAVED%/*}"
        grep -F -f <(ours) "$P/prefs.js" > "$SAVED" 2>/dev/null || true
    fi
    # (After a last line without its newline, the start marker would join that line, and the
    # block couldn't be found again: not even to remove it.)
    [ -z "$(tail -c1 "$P/user.js")" ] || echo >> "$P/user.js"
    { echo "$BEGIN"; cat "$TWEAK_DIR/user.js"; echo "$END"; } >> "$P/user.js"
    say "$(t 'Anti-fingerprinting settings written to %s' "$P/user.js")"
else
    say "$(t 'Removed our settings from user.js.')"
    # Firefox copied them into prefs.js, where they'd stay: take out the same names there too,
    # and put back yours. (Only while it's closed: it rewrites prefs.js when it quits.)
    if pgrep -f '/app/lib/firefox/firefox ' >/dev/null; then
        warn "$(t 'Firefox is running: quit it and run this again, or reset the settings in about:config.')"
    elif [ -f "$P/prefs.js" ]; then
        cp "$P/prefs.js" "$P/prefs.js.frame-tweaks-bak"
        grep -vF -f <(ours) "$P/prefs.js.frame-tweaks-bak" > "$P/prefs.js" || true
        say "$(t 'Reset them in prefs.js too (the previous copy: prefs.js.frame-tweaks-bak).')"
        if [ -s "$SAVED" ]; then
            cat "$SAVED" >> "$P/prefs.js"
            say "$(t 'Put back the values you had set yourself before: %s' "$(sed -n 's/^user_pref("\([^"]*\)".*/\1/p' "$SAVED" | paste -sd, - | sed 's/,/, /g')")"
        fi
        rm -f "$SAVED"
    fi
fi
if pgrep -f '/app/lib/firefox/firefox ' >/dev/null; then warn "$(t 'Firefox is running: restart it to apply.')"; fi
