#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/adb" ] || status_missing "$(t 'adb not installed')"
"$BIN/adb" version >/dev/null 2>&1 || status_warn "$(t 'adb installed but does not run (re-run ./install.sh adb-scrcpy)')"
# (adb comes first in install.sh: an install that stopped later has it, but no Android Mirror to open)
[ -x "$BIN/phone" ] && [ -f "$APPS/android-mirror.desktop" ] ||
    status_warn "$(t 'phone launcher or its menu entry missing (re-run ./install.sh adb-scrcpy)')"
brew_cmd scrcpy >/dev/null || status_warn "$(t 'scrcpy missing (brew install scrcpy)')"
# phone-touch (the VR extras) only runs with the scrcpy major version it was tested with.
exe=$(brew_cmd scrcpy || echo "${BREW%/brew}/scrcpy")
v=$("$exe" --version 2>/dev/null | sed -n '1s/^scrcpy \([^ ]*\).*/\1/p' || true)
tested=$(sed -n 's/^scrcpy=//p' "$REPO_DIR/lib/tested-versions")
[ -z "$v" ] || [ "${v%%.*}" = "${tested%%.*}" ] ||
    status_warn "$(t 'scrcpy %s is untested (Frame Tweaks is tested with %s.x): the mirror works, its VR laser clicks and joystick scrolling are off' "$v" "${tested%%.*}")"
status_ok "$(t 'adb %s, scrcpy%s, phone launcher' "$("$BIN/adb" version | sed -n "2s/Version //p")" "${v:+ $v}")"
