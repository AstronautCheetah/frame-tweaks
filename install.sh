#!/bin/bash
# Install one or more components:  ./install.sh dictation arrowpad
# With no arguments, lists the components.
cd "$(dirname "$0")"
COMPONENTS=(dictation arrowpad full-keyboard cursor adb-scrcpy wallet signal claude-desktop tools ydotool)
if [ $# -eq 0 ]; then
    echo "Usage: ./install.sh <component>... | all"
    for c in "${COMPONENTS[@]}"; do printf '  %-15s %s\n' "$c" "$(sed -n '2s/^# //p' "$c/install.sh")"; done
    exit 0
fi
[ "$1" = all ] && set -- "${COMPONENTS[@]}"
for c in "$@"; do
    [ -x "$c/install.sh" ] || { echo "unknown component: $c" >&2; exit 1; }
    echo; echo "### $c"; "./$c/install.sh" || exit 1
done
