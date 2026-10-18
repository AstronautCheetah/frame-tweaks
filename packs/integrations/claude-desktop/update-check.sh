#!/bin/bash
# Prints "<installed> <latest>" for the installer window's update hint (network; quiet on failure).
# The latest is what an update would install: claude-desktop-update picks it (Claude Desktop's own
# entry in Anthropic's list, the newest as dpkg orders versions, over HTTPS only), so the hint
# can't offer what the update then won't take. (A time limit, as the window waits 20 seconds.)
cur=$(cat "$HOME/.local/opt/claude-desktop/.deb-version" 2>/dev/null) || exit 1
latest=$(timeout 15 "$(dirname "$0")/claude-desktop-update" --print-latest 2>/dev/null) || exit 1
[ -n "$latest" ] && echo "$cur $latest"
