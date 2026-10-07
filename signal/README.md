# Signal: encrypted key storage

The Flathub build of Signal Desktop asks on every launch whether to use the
**plaintext** password store. Choosing it leaves the key to your message database
unencrypted on disk. This tweak makes it use **KDE Wallet** instead:

```sh
./install.sh signal
signal/check          # verify: "OK: database key is encrypted via kwallet6"
```

It sets `SIGNAL_PASSWORD_STORE=kwallet6` as a per-user Flatpak override (same as
doing it in Flatseal). The startup warning goes away and Signal stores its database
key in your wallet.

**Already using Signal with plaintext?** The installer handles it. Signal migrates
by itself over two launches: the first adds the wallet-encrypted key (keeping the
plaintext one until it's confirmed), the second deletes the plaintext key. The installer
runs both launches for you, then checks the result.

## How secure is it?
The key is only as protected as your wallet. If `kdewallet` was created with an
**empty password**, it's stored without real protection. With a password, you'll be
asked for it once per session when Signal (or another app) first opens the wallet.
You can change it in *System Settings → KDE Wallet → Wallet Manager → Change Password*.
Signal's warning about "experimental" backends mainly concerns GNOME libsecret on
other desktops. On KDE, kwallet6 is the native, intended backend.
