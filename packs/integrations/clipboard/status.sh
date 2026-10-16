#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
[ -x "$BIN/clipboard-sync" ] || status_missing "$(t '%s not installed' clipboard-sync)"
if ! pgrep -u "$(id -u)" -x clipboard-sync >/dev/null; then
    # (it starts with desktop mode: not running without it is as it should be)
    pgrep -u "$(id -u)" -x ksmserver >/dev/null || status_ok "$(t 'installed; starts with desktop mode')"
    status_warn "$(t 'not running, though desktop mode is (Restart starts it)')"
fi
n=$(pgrep -u "$(id -u)" -x clipboard-sync | wc -l)
[ "$n" -le 2 ] || status_warn "$(t '%s copies running (Restart fixes it)' "$n")"   # (each forks one helper)
ver=$(cat "$HOME/.local/share/frame-tweaks/clipboard-sync/VERSION" 2>/dev/null || true)   # (|| true: with no such file, set -e stopped the check here)
if [ -z "$ver" ]; then              # (built on the Frame by an older version: its changes, if it has them)
    patched=$(cat "$HOME/.local/share/frame-tweaks/src/clipboard-sync/.sft-patched" 2>/dev/null || true)
    [[ $patched == *keep-images* ]] || status_warn "$(t 'older build: replaces copied images with text (Reinstall fixes it)')"
    [[ $patched == *sync-sessions* ]] ||
        status_warn "$(t 'older build: files and pictures stay in their session, and a copied file can paste only as text (Reinstall fixes it)')"
fi
status_ok "$(t '%s running' "clipboard-sync${ver:+ $ver}")"
