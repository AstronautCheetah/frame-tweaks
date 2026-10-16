#!/bin/bash
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
# (Not on a reinstall, ↻: the entries stay protected, and the wallet's programs they run come back
# with the install. Its install protects only KWalletManager, Signal and Claude again, so the
# protection you'd added to others was gone.)
if [ -x "$BIN/wallet-launcher" ] && [ -z "${FRAME_TWEAKS_REINSTALL:-}" ]; then
    # (by file, not --list's columns: an entry's name can have spaces, e.g. "My App.desktop")
    for f in "$APPS"/*.desktop; do
        grep -q '^X-FrameTweaks-Wallet=true' "$f" 2>/dev/null && "$BIN/wallet-launcher" --remove "$(basename "$f" .desktop)"
    done
    rmdir "$LAUNCHER_BUILT" 2>/dev/null || true      # (each --remove took its app's copy)
fi
sysctl_user stop wallet-autolock.timer 2>/dev/null || true
sysctl_user disable --now wallet-lock-sync 2>/dev/null || true
sysctl_user disable --now app-timers 2>/dev/null || true
# git's credential helper goes back from the gh wrapper to the real gh, the one the wrapper runs
# (not the one on PATH: the installer window's Konsole has no Homebrew on it, and the helper was
# left naming the wrapper this deletes). Without it, the helper lines naming the wrapper go: git
# then asks for a login, rather than run a program that's gone.
REAL_GH="" ours=""
if grep -qs with-keyring "$BIN/gh"; then       # (only the wrapper: a gh of your own stays)
    ours=1
    REAL_GH=$(sed -n 's|^exec "$HOME/.local/bin/with-keyring" \(/.*\) "\$@"$|\1|p' "$BIN/gh")
fi
[ -x "$REAL_GH" ] && ! [ "$REAL_GH" -ef "$BIN/gh" ] || REAL_GH=""
for h in https://github.com https://gist.github.com; do
    git config --global --fixed-value --get-all "credential.$h.helper" "!$BIN/gh auth git-credential" >/dev/null 2>&1 || continue
    if [ -n "$REAL_GH" ]; then
        git config --global --fixed-value --replace-all "credential.$h.helper" "!$REAL_GH auth git-credential" "!$BIN/gh auth git-credential"
    else
        git config --global --fixed-value --unset-all "credential.$h.helper" "!$BIN/gh auth git-credential"
    fi
done
[ -z "$ours" ] || remove_files "$BIN/gh"
restore_kconfig wallet
remove_icon frame-tweaks-lock
remove_desktop wallet-lock.desktop
remove_files "$HOME/.config/systemd/user/wallet-lock-sync.service" "$HOME/.config/systemd/user/app-timers.service" "$BIN/app-timers" "$BIN/with-keyring" "$BIN/wallet-unlock" "$BIN/wallet-gate" "$BIN/wallet-launcher" "$BIN/frame-outer-bus"
say "$(t 'Kept KWalletManager (%s) and the wallet itself. gh tokens stay in the wallet.' "flatpak uninstall org.kde.kwalletmanager")"
warn "$(t 'Signal still needs the wallet: keep its kwallet6 setting (see %s).' signal/README.md)"
