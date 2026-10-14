#!/bin/bash
# Claude Code (command line) via Anthropic's native installer: ~/.local/bin/claude, self-updating.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
if have=$(command -v claude) && [ "$have" != "$BIN/claude" ]; then
    say "$(t 'Claude Code is already installed at %s (%s); leaving it as it is.' "$have" "$(claude --version 2>/dev/null)")"
    exit 0
fi
say "$(t "Installing Claude Code (Anthropic's installer, into your home folder)")"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
curl -fsSL https://claude.ai/install.sh -o "$T/install.sh" || die "$(t "Couldn't download Anthropic's installer.")"
bash "$T/install.sh" || die "$(t "Anthropic's installer failed (see above).")"
"$BIN/claude" --version
t 'Done. Open a terminal (Konsole) and run: claude
The first run asks you to log in with your Claude account in a browser.'; echo
