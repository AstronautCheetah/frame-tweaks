#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/clipboard-sync" ] || status_missing "$(t '%s not installed' clipboard-sync)"
pgrep -u "$(id -u)" -x clipboard-sync >/dev/null || status_warn "$(t 'installed but not running (starts with desktop mode)')"
n=$(pgrep -u "$(id -u)" -x clipboard-sync | wc -l)
[ "$n" -le 2 ] || status_warn "$(t '%s copies running (Restart fixes it)' "$n")"   # (each forks one helper)
patched=$(cat "$HOME/.local/share/frame-tweaks/src/clipboard-sync/.sft-patched" 2>/dev/null)
[[ $patched == *keep-images* ]] || status_warn "$(t 'older build: replaces copied images with text (Reinstall fixes it)')"
[[ $patched == *keep-source* ]] ||
    status_warn "$(t 'older build: a copied file or formatted text pastes only as text (Reinstall fixes it)')"
status_ok "$(t '%s running' clipboard-sync)"
