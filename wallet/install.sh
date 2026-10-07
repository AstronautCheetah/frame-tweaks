#!/bin/bash
# One KDE wallet for both sessions (steam-frame-nix approach) + KWalletManager.
source "$(dirname "$0")/../lib/common.sh"
ensure_path
install -m755 "$REPO_DIR/wallet/frame-outer-bus" "$REPO_DIR/wallet/wallet-launcher" "$BIN/"

say "Installing KWalletManager (Flathub)"
flatpak install -y --noninteractive flathub org.kde.kwalletmanager

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
