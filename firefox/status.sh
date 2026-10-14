#!/bin/bash
source "$(dirname "$0")/../lib/common.sh"
ROOT="$HOME/.var/app/org.mozilla.firefox/config/mozilla/firefox"
[ -d "$ROOT" ] || ROOT="$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox"     # (as install.sh)
[ -f "$ROOT/installs.ini" ] || status_missing "no Firefox (Flathub) profile"
P="$ROOT/$(grep -m1 "^Default=" "$ROOT/installs.ini" | cut -d= -f2)"
grep -q "frame-tweaks" "$P/user.js" 2>/dev/null || status_missing "anti-fingerprinting settings not applied"
grep -q "privacy.resistFingerprinting\", true" "$P/prefs.js" 2>/dev/null || status_warn "applied; restart Firefox to activate"
status_ok "resistFingerprinting active"
