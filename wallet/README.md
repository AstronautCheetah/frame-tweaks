# Wallet: one KDE wallet for both sessions

The Frame runs two sessions at once: Steam/VR on the outer D-Bus and the nested
Plasma desktop on its own private bus. An app started from the desktop talks to a
**second** `kwalletd6` on the private bus. Its secrets are invisible to the same app
started from VR, and two daemons writing the same wallet file can overwrite each
other. This follows [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s
launcher approach (`keyring.enable`), without needing Nix:

```sh
./install.sh wallet
wallet-launcher --list            # apps currently routed to the shared wallet
wallet-launcher org.example.App   # add one (--electron adds --password-store=kwallet6)
wallet-launcher --remove org.example.App
```

- **`wallet-launcher`** writes an override menu entry (`~/.local/share/applications/<id>.desktop`)
  whose command runs through `frame-outer-bus`. For Flatpaks it also adds
  `--talk-name=org.kde.kwalletd6 --talk-name=org.freedesktop.secrets`. Host-app
  originals are backed up in `~/.local/share/applications/.wallet-launcher-originals/`.
- **`frame-outer-bus <cmd>`** runs a command on the outer session's D-Bus **and** runtime dir.
  It keeps the window on the display it was launched from by pinning `WAYLAND_DISPLAY`
  as an absolute path.
- **KWalletManager** (Flathub) is installed and routed to the shared wallet, so you can
  see what's stored and set a password. SteamOS has no wallet GUI or settings page.

Installed by default for: KWalletManager, Signal and Claude Desktop (when present).

## Auto-close
The installer sets KWallet to close the wallet after **4 hours unused**
(`WALLET_IDLE_MINUTES=60 ./install.sh wallet` to change; stored in `~/.config/kwalletrc` as
`Close When Idle` / `Idle Timeout`). The timer restarts whenever any app reads the wallet.
Once it closes, the next app that needs it asks for the password.

## Security: set a wallet password
SteamOS seeds every Frame with the same stock `kdewallet` (`steamos-setup-kwallet`
copies it from `/usr/share/kwalletd`), and it opens **without a password**. Until you
set one (KWalletManager → *kdewallet* → *Change Password*), anything "stored in the
wallet" is only obscured, not protected. With a password, the wallet asks once per
session. The prompt comes from the outer session's wallet, so it can show up as a VR
window.

## Gotcha found the hard way
Moving only `DBUS_SESSION_BUS_ADDRESS` (as a plain `env` prefix) hangs Flatpak Electron
apps such as Signal at startup. `flatpak run` registers the instance under
`$XDG_RUNTIME_DIR/.flatpak`, which in the nested desktop is `/run/user/$UID/nested_plasma`,
so the outer bus's flatpak-portal can't find it (`Spawn: Could not find requesting pid`)
and Chromium's zygote never starts. `frame-outer-bus` switches `XDG_RUNTIME_DIR` as well.

Caveat: apps routed to the outer bus use that session's portals and notifications, so
some desktop integration (e.g. a tray icon, dark-mode detection) may differ.
