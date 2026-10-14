#!/bin/bash
# Claude Desktop (official Linux build, arm64), unpacked into ~/.local/opt.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
install_i18n         # (claude-desktop-update's messages in your language)
install -m755 "$TWEAK_DIR/claude-desktop-update" "$BIN/claude-desktop-update"
"$BIN/claude-desktop-update"
say "$(t 'Update later with: %s' claude-desktop-update)"
