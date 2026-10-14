#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
if [ -e "$BIN/claude" ]; then
    remove_files "$BIN/claude" "$HOME/.local/share/claude"
elif [ -x /home/linuxbrew/.linuxbrew/bin/claude ]; then
    say "$(t 'Claude Code was installed with Homebrew; remove it with: %s' 'brew uninstall --cask claude-code@latest')"
fi
say "$(t 'Kept your login and settings (~/.claude, ~/.claude.json).')"
