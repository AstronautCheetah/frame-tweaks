#!/bin/bash
# One KDE wallet for both sessions (steam-frame-nix approach) + KWalletManager.
source "$(dirname "$0")/../lib/common.sh"
ensure_path
install -m755 "$REPO_DIR/wallet/frame-outer-bus" "$REPO_DIR/wallet/wallet-launcher" "$REPO_DIR/wallet/wallet-gate" "$BIN/"
ensure_tweaks_venv
install_py_tool "$REPO_DIR/wallet/wallet-unlock"
install -m755 "$REPO_DIR/wallet/with-keyring" "$BIN/"

# gh (Homebrew) would store its token in plain text: no Secret Service on the desktop's bus.
REAL_GH=$(PATH="${PATH//$BIN:/}" command -v gh || true)
if [ -n "$REAL_GH" ]; then
    printf '#!/bin/sh\n# gh with its token in the shared KDE wallet (see with-keyring)\nexec "$HOME/.local/bin/with-keyring" %s "$@"\n' "$REAL_GH" > "$BIN/gh"
    chmod 755 "$BIN/gh"
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
kwriteconfig6 --file kwalletrc --group Wallet --key "Close When Idle" true
kwriteconfig6 --file kwalletrc --group Wallet --key "Idle Timeout" "$IDLE"
for bus in "${DBUS_SESSION_BUS_ADDRESS:-}" "unix:path=/run/user/$(id -u)/bus"; do
    [ -n "$bus" ] && DBUS_SESSION_BUS_ADDRESS="$bus" qdbus6 org.kde.kwalletd6 /modules/kwalletd6 \
        org.kde.KWallet.reconfigure >/dev/null 2>&1 || true
done
say "Wallet closes after $IDLE minutes unused (WALLET_IDLE_MINUTES=… to change)"

# Apps known to keep secrets in the wallet; only those installed get a launcher.
apps=(org.kde.kwalletmanager)
flatpak info org.signal.Signal >/dev/null 2>&1 && apps+=(org.signal.Signal)
[ -f "$APPS/com.anthropic.Claude.desktop" ] && apps+=(com.anthropic.Claude)
"$BIN/wallet-launcher" "${apps[@]}"
cat <<MSG

Add other wallet-using apps with:  wallet-launcher <app-id>   (--electron for Electron apps)
SteamOS's stock wallet has an EMPTY password. To actually protect it, open
KWalletManager → kdewallet → Change Password.
MSG
