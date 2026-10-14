#!/bin/bash
# One KDE wallet for both sessions (steam-frame-nix approach) + KWalletManager.
source "${FRAME_TWEAKS_LIB:-$(dirname "$0")/../../../lib}/common.sh"
ensure_path
install -m755 "$TWEAK_DIR/frame-outer-bus" "$TWEAK_DIR/wallet-launcher" "$TWEAK_DIR/wallet-gate" \
    "$TWEAK_DIR/app-timers" "$BIN/"
ensure_tweaks_venv
install_py_tool "$TWEAK_DIR/wallet-unlock"
install -m755 "$TWEAK_DIR/with-keyring" "$BIN/"

# Closing the wallet (KWalletManager, idle timeout) only closes kwalletd6's view; ksecretd
# stays unlocked. This service turns every close into a real lock.
mkdir -p "$HOME/.config/systemd/user"
cp "$TWEAK_DIR/wallet-lock-sync.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable --now wallet-lock-sync
sysctl_user restart wallet-lock-sync
# App timers (set in the installer window's Wallet apps page): idle while none are set.
cp "$TWEAK_DIR/app-timers.service" "$HOME/.config/systemd/user/"
sysctl_user daemon-reload
sysctl_user enable --now app-timers
sysctl_user restart app-timers
install_icon frame-tweaks-lock
install_desktop "$TWEAK_DIR/wallet-lock.desktop"

# gh (Homebrew) would store its token in plain text: no Secret Service on the desktop's bus.
REAL_GH=$(PATH="${PATH//$BIN:/}" command -v gh || true)
if [ -n "$REAL_GH" ]; then
    printf '#!/bin/sh\n# gh with its token in the shared KDE wallet (see with-keyring)\nexec "$HOME/.local/bin/with-keyring" %s "$@"\n' "$REAL_GH" | write_file "$BIN/gh" 755
    for h in https://github.com https://gist.github.com; do
        git config --global --get "credential.$h.helper" >/dev/null 2>&1 &&
            git config --global --replace-all "credential.$h.helper" "!$BIN/gh auth git-credential" '^!.*gh auth git-credential$'
    done
    if grep -q oauth_token "$HOME/.config/gh/hosts.yml" 2>/dev/null; then
        say "Moving gh's plain-text token into the wallet"
        "$REAL_GH" auth token | "$BIN/gh" auth login --with-token --hostname github.com
    fi
fi

say "Installing KWalletManager (Flathub)"
flatpak install -y --noninteractive flathub org.kde.kwalletmanager

# Lock the wallet after it has gone unused for a while (both daemons read kwalletrc).
IDLE=${WALLET_IDLE_MINUTES:-240}
save_kconfig wallet kwalletrc Wallet "Close When Idle" "Idle Timeout"     # restored on uninstall
# (Unless auto-lock was turned off on the Wallet apps page: then it stays off.)
autolock=$(sed -n 's/^WALLET_AUTOLOCK=//p' "$HOME/.config/frame-tweaks/wallet.conf" 2>/dev/null | tail -1 || true)
kwriteconfig6 --file kwalletrc --group Wallet --key "Close When Idle" "$([ "$autolock" = 0 ] && echo false || echo true)"
kwriteconfig6 --file kwalletrc --group Wallet --key "Idle Timeout" "$IDLE"
# Reconfigure only wallet services that are already running: calling one on the desktop's
# bus would start a second wallet service there (two copies writing one wallet file).
for bus in "${DBUS_SESSION_BUS_ADDRESS:-}" "unix:path=/run/user/$(id -u)/bus"; do
    [ -n "$bus" ] || continue
    busctl --address="$bus" status org.kde.kwalletd6 >/dev/null 2>&1 || continue
    DBUS_SESSION_BUS_ADDRESS="$bus" qdbus6 org.kde.kwalletd6 /modules/kwalletd6 \
        org.kde.KWallet.reconfigure >/dev/null 2>&1 || true
done
say "Wallet closes after $IDLE minutes unused (WALLET_IDLE_MINUTES=… to change)"

# Apps known to keep secrets in the wallet; only those installed get a launcher.
apps=(org.kde.kwalletmanager)
flatpak info org.signal.Signal >/dev/null 2>&1 && apps+=(org.signal.Signal)
[ -f "$APPS/com.anthropic.Claude.desktop" ] && apps+=(com.anthropic.Claude)
# --gate: open through our unlock dialog first, so these never trigger ksecretd's own
# prompt (the one that floats in VR and blocks every other unlock while it's open).
if ! "$BIN/wallet-launcher" --gate "${apps[@]}"; then
    warn "Couldn't put the password gate on all of: ${apps[*]}. Those without a menu entry yet"
    warn "aren't gated; once they're installed, run: wallet-launcher --gate <app-id>"
fi
cat <<MSG

Add other wallet-using apps with:  wallet-launcher <app-id>   (--electron for Electron apps)
SteamOS's stock wallet has an EMPTY password. To actually protect it, open
KWalletManager → kdewallet → Change Password.
MSG
