#!/bin/bash
# Firefox (Flathub): anti-fingerprinting user.js in the default profile.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
APP="$HOME/.var/app/org.mozilla.firefox"
ROOT="$APP/config/mozilla/firefox"
[ -d "$ROOT" ] || ROOT="$APP/.mozilla/firefox"
[ -f "$ROOT/installs.ini" ] || die "$(t 'No Firefox profile yet: start Firefox (Flathub) once, then re-run.')"

# Firefox's sandbox can write everything in its folder, and this runs outside the sandbox: a link
# planted there (a profile path leading out of it, a file that leads elsewhere) would have this
# write, or copy, files of yours outside it. So nothing there is followed: this goes into the
# profile, which must be a folder inside Firefox's own (go), and works there; a file must be a
# plain one, copied out to work on (load); and it's written as a new file renamed over the old
# one (put), which replaces a link rather than writing through it.
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
refuse() {
    die "$(t "%s is a link, or not a plain file. Firefox's sandbox can write there, so Frame Tweaks leaves the profile alone: remove it, then run this again." "$1")"
}
outside() { die "$(t "Firefox's profile %s isn't a folder inside Firefox's own, so Frame Tweaks leaves it alone." "$1")"; }
# go DIR TOP: into DIR, which must be a folder inside TOP; here: that folder, as the kernel has
# it. (Not cd's $PWD: cd works that out from the path, so a link switched while it went in could
# have $PWD name a folder inside while this went into one outside.)
go() { cd -P -- "$1" && here=$(realpath -e .) && [[ $here == "$2"/* ]]; }
# plain NAME: NAME here is a plain file, or isn't there.
plain() { if [ -L "$1" ] || { [ -e "$1" ] && [ ! -f "$1" ]; }; then refuse "$here/$1"; fi; }
# load NAME: $WORK/NAME, a copy of NAME here (empty if there's none). (Read by dd, which neither
# follows a link nor waits on a FIFO, either of them put there after plain looked.)
load() {
    : > "$WORK/$1"
    [ -e "$1" ] || [ -L "$1" ] || return 0
    plain "$1"
    dd if="$1" of="$WORK/$1" iflag=nofollow,nonblock status=none 2>/dev/null || refuse "$here/$1"
}
# put NAME: what's on stdin becomes NAME here. (The new file is one that wasn't there: a link
# put in its place makes this fail rather than write through it.)
put() {
    local new
    new=$(mktemp -u ".$1.XXXXXXXX")
    if (set -C; umask 077; cat > "$new") && mv -fT -- "$new" "$1"; then return 0; fi
    rm -f -- "$new"
    die "$(t "Couldn't write %s" "$here/$1")"
}
app=$(realpath -e -- "$APP")
go "$ROOT" "$app" || outside "$ROOT"
load installs.ini
PROFILE=$(grep -m1 '^Default=' "$WORK/installs.ini" | cut -d= -f2) || true
[ -n "$PROFILE" ] || die "$(t 'No Firefox profile yet: start Firefox (Flathub) once, then re-run.')"
P="$ROOT/$PROFILE"
case "/$PROFILE/" in //*|*/../*) outside "$P" ;; esac          # (a path from /, or through ..)
top=$here
[ -d "./$PROFILE" ] || die "$(t 'Profile %s not found' "$P")"
go "./$PROFILE" "$top" || outside "$P"

BEGIN="// >>> frame-tweaks"; END="// <<< frame-tweaks"
load user.js
# Firefox copies our settings into prefs.js (as user_pref("NAME", ...) lines). Those of them you
# had set yourself before the first install (HTTPS-only mode, say) are recorded in SAVED as they
# were, and put back when the tweak is removed. (Recorded once, while our block isn't in user.js
# yet: once it is, prefs.js has Firefox's copies of ours. Installed before this was recorded,
# removing resets them all.)
names=$(sed -n 's/^user_pref("\([^"]*\)".*/\1/p' "$TWEAK_DIR/user.js")
ours() { printf 'user_pref("%s",\n' $names; }        # (the start of their lines)
SAVED="$BACKUPS/firefox/${P#"$HOME"/}/prefs.js.before"
installed=; grep -qE '^// >>> (steam-)?frame-tweaks' "$WORK/user.js" && installed=1
# Replace our block (between markers) and keep anything else the user has in user.js. (Before
# 0.5 the markers said steam-frame-tweaks: those blocks go too.) A start marker without its end
# would have sed delete everything after it, the user's own lines too: stop instead.
for m in frame-tweaks steam-frame-tweaks; do
    awk -v b="// >>> $m" -v e="// <<< $m" 'index($0, b) == 1 { if (open) exit 1; open = 1 }
        index($0, e) == 1 { open = 0 } END { exit open }' "$WORK/user.js" ||
        die "$(t "%s has a '%s' line without its '%s' line: fix that by hand, then run this again." "$P/user.js" "// >>> $m" "// <<< $m")"
done
sed -e "\|^$BEGIN|,\|^$END|d" -e "\|^// >>> steam-frame-tweaks|,\|^// <<< steam-frame-tweaks|d" "$WORK/user.js" > "$WORK/user.js.new"
if [ "${1:-}" != "--remove" ]; then
    if [ -z "$installed" ] && [ ! -e "$SAVED" ]; then
        load prefs.js
        mkdir -p "${SAVED%/*}"
        grep -F -f <(ours) "$WORK/prefs.js" > "$SAVED" || true
    fi
    # (After a last line without its newline, the start marker would join that line, and the
    # block couldn't be found again: not even to remove it.)
    [ -z "$(tail -c1 "$WORK/user.js.new")" ] || echo >> "$WORK/user.js.new"
    { cat "$WORK/user.js.new"; echo "$BEGIN"; cat "$TWEAK_DIR/user.js"; echo "$END"; } | put user.js
    say "$(t 'Anti-fingerprinting settings written to %s' "$P/user.js")"
else
    # Firefox copied them into prefs.js, where they'd stay: take out the same names there too,
    # and put back yours. (Only while it's closed: it rewrites prefs.js when it quits. Its files
    # are checked before user.js changes, so one refused leaves the profile as it was.)
    running=; if pgrep -f '/app/lib/firefox/firefox ' >/dev/null; then running=1; fi
    prefs=
    if [ -z "$running" ] && { [ -e prefs.js ] || [ -L prefs.js ]; }; then
        load prefs.js; plain prefs.js.frame-tweaks-bak; prefs=1
    fi
    put user.js < "$WORK/user.js.new"
    say "$(t 'Removed our settings from user.js.')"
    if [ -n "$running" ]; then
        warn "$(t 'Firefox is running: quit it and run this again, or reset the settings in about:config.')"
    elif [ -n "$prefs" ]; then
        put prefs.js.frame-tweaks-bak < "$WORK/prefs.js"
        { grep -vF -f <(ours) "$WORK/prefs.js" || true; if [ -s "$SAVED" ]; then cat "$SAVED"; fi; } | put prefs.js
        say "$(t 'Reset them in prefs.js too (the previous copy: prefs.js.frame-tweaks-bak).')"
        if [ -s "$SAVED" ]; then
            say "$(t 'Put back the values you had set yourself before: %s' "$(sed -n 's/^user_pref("\([^"]*\)".*/\1/p' "$SAVED" | paste -sd, - | sed 's/,/, /g')")"
        fi
        rm -f "$SAVED"
    fi
fi
if pgrep -f '/app/lib/firefox/firefox ' >/dev/null; then warn "$(t 'Firefox is running: restart it to apply.')"; fi
