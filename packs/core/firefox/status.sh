#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ROOT="$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"
[ -d "$ROOT" ] || ROOT="$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox"     # (as install.sh)
[ -f "$ROOT/installs.ini" ] || status_missing "$(t 'no Firefox (Flathub) profile')"
P=$(grep -m1 "^Default=" "$ROOT/installs.ini" | cut -d= -f2) || status_missing "$(t 'no Firefox (Flathub) profile')"
P="$ROOT/$P"
grep -q "frame-tweaks" "$P/user.js" 2>/dev/null || status_missing "$(t 'anti-fingerprinting settings not applied')"
grep -q "privacy.resistFingerprinting\", true" "$P/prefs.js" 2>/dev/null || status_warn "$(t 'applied; restart Firefox to activate')"
status_ok "$(t 'resistFingerprinting active')"
