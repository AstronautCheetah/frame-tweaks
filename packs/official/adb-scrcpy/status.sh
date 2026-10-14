#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/adb" ] || status_missing "adb not installed"
"$BIN/adb" version >/dev/null 2>&1 || status_warn "adb installed but does not run (re-run ./install.sh adb-scrcpy)"
command -v scrcpy >/dev/null || [ -x /home/linuxbrew/.linuxbrew/bin/scrcpy ] || status_warn "scrcpy missing (brew install scrcpy)"
# phone-touch (the VR extras) only runs with the scrcpy major version it was tested with.
exe=$(command -v scrcpy || echo /home/linuxbrew/.linuxbrew/bin/scrcpy)
v=$("$exe" --version 2>/dev/null | sed -n '1s/^scrcpy \([^ ]*\).*/\1/p' || true)
tested=$(sed -n 's/^scrcpy=//p' "$REPO_DIR/lib/tested-versions")
[ -z "$v" ] || [ "${v%%.*}" = "${tested%%.*}" ] ||
    status_warn "scrcpy $v is untested (Frame Tweaks is tested with ${tested%%.*}.x): the mirror works, its VR laser clicks and joystick scrolling are off"
status_ok "adb $("$BIN/adb" version | sed -n "2s/Version //p"), scrcpy${v:+ $v}, phone launcher"
