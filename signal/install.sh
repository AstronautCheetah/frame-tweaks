#!/bin/bash
# Signal (Flathub): keep its database key in KDE Wallet instead of plaintext on disk.
source "$(dirname "$0")/../lib/common.sh"
APP=org.signal.Signal
CFG="$HOME/.var/app/$APP/config/Signal/config.json"

flatpak info "$APP" >/dev/null 2>&1 || die "Install Signal first (Discover, or: flatpak install flathub $APP)"
[ "$(qdbus6 org.kde.kwalletd6 /modules/kwalletd6 org.kde.KWallet.isEnabled 2>/dev/null)" = true ] ||
    die "KDE Wallet is disabled; enable it in System Settings → KDE Wallet first."

say "Telling Signal to use KDE Wallet (kwallet6)"
flatpak override --user --env=SIGNAL_PASSWORD_STORE=kwallet6 "$APP"

# Signal migrates on its own: 1st launch adds encryptedKey (keeping the plaintext
# key until decryption is confirmed), 2nd launch deletes the plaintext key.
if [ -f "$CFG" ]; then
    flatpak kill "$APP" 2>/dev/null || true
    for run in 1 2; do
        say "Migrating existing key: Signal launch $run/2"
        (cd ~ && setsid -f flatpak run "$APP" >/dev/null 2>&1 </dev/null)
        sleep 15; flatpak kill "$APP" 2>/dev/null || true; sleep 2
    done
fi
"$REPO_DIR/signal/check"
