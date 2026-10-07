#!/bin/bash
# Signal (Flathub): database key in the shared KDE wallet instead of plaintext on disk.
source "$(dirname "$0")/../lib/common.sh"
APP=org.signal.Signal
CFG="$HOME/.var/app/$APP/config/Signal/config.json"

flatpak info "$APP" >/dev/null 2>&1 || die "Install Signal first (Discover, or: flatpak install flathub $APP)"
[ -x "$BIN/wallet-launcher" ] || "$REPO_DIR/wallet/install.sh"

say "Telling Signal to use KDE Wallet (kwallet6)"
flatpak override --user --env=SIGNAL_PASSWORD_STORE=kwallet6 "$APP"
"$BIN/wallet-launcher" "$APP"
LAUNCH=$(sed -n 's/^Exec=//p' "$APPS/$APP.desktop" | head -1 | sed 's/ @@u %U @@//')

# Signal migrates on its own: 1st launch adds encryptedKey (keeping the plaintext
# key until decryption is confirmed), 2nd launch deletes the plaintext key.
if [ -f "$CFG" ] && grep -q '"key"' "$CFG"; then
    flatpak kill "$APP" 2>/dev/null || true
    for run in 1 2; do
        say "Migrating existing key: Signal launch $run/2"
        (cd ~ && eval "setsid -f $LAUNCH" >/dev/null 2>&1 </dev/null)
        sleep 20; flatpak kill "$APP" 2>/dev/null || pkill -f "/app/Signal/signal-desktop" || true; sleep 2
    done
fi
"$REPO_DIR/signal/check"
