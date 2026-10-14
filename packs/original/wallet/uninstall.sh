#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
if [ -x "$BIN/wallet-launcher" ]; then
    for app in $("$BIN/wallet-launcher" --list | cut -d" " -f1); do "$BIN/wallet-launcher" --remove "$app"; done
fi
sysctl_user stop wallet-autolock.timer 2>/dev/null || true
sysctl_user disable --now wallet-lock-sync 2>/dev/null || true
sysctl_user disable --now app-timers 2>/dev/null || true
REAL_GH=$(PATH="${PATH//$BIN:/}" command -v gh || true)
if [ -n "$REAL_GH" ] && [ -f "$BIN/gh" ]; then
    for h in https://github.com https://gist.github.com; do
        git config --global --get "credential.$h.helper" >/dev/null 2>&1 &&
            git config --global --replace-all "credential.$h.helper" "!$REAL_GH auth git-credential" "^!.*gh auth git-credential$"
    done
fi
restore_kconfig wallet
remove_files "$ICONS/256x256/apps/frame-tweaks-lock.png" "$HOME/.config/systemd/user/wallet-lock-sync.service" "$HOME/.config/systemd/user/app-timers.service" "$BIN/app-timers" "$APPS/wallet-lock.desktop" "$BIN/gh" "$BIN/with-keyring" "$BIN/wallet-unlock" "$BIN/wallet-gate" "$BIN/wallet-launcher" "$BIN/frame-outer-bus"
say "$(t 'Kept KWalletManager (%s) and the wallet itself. gh tokens stay in the wallet.' "flatpak uninstall org.kde.kwalletmanager")"
warn "$(t 'Signal still needs the wallet: keep its kwallet6 setting (see %s).' signal/README.md)"
