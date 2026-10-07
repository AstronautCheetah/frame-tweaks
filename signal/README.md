# Signal: encrypted key storage

The Flathub build of Signal Desktop asks on every launch whether to use the
**plaintext** password store. Choosing it leaves the key to your message database
unencrypted on disk. This tweak makes it use **KDE Wallet** instead:

```sh
./install.sh signal
signal/check          # verify: "OK: database key is encrypted via kwallet6"
```

It sets `SIGNAL_PASSWORD_STORE=kwallet6` as a per-user Flatpak override (same as
doing it in Flatseal), so the startup warning goes away and Signal stores its database
key in your wallet. It also gives Signal a [wallet launcher](../wallet/), so it uses the
same wallet whether you start it from the desktop or from VR.

**Already using Signal with plaintext?** The installer handles it. Signal migrates
by itself over two launches: the first adds the wallet-encrypted key (keeping the
plaintext one until it's confirmed), the second deletes the plaintext key. The installer
runs both launches for you, then checks the result.

## Idle lock (`signal-guard`)
Signal Desktop has no lock of its own (Signal has declined to add one), so the Signal
launcher starts `signal-guard` alongside it. It quits Signal (gracefully) after
**15 minutes** without keyboard, mouse or controller input. Reopening Signal then needs
the wallet, so if the wallet is locked you're asked for its password.

```sh
signal-guard --status          # guard state and current idle time
```

`~/.config/signal-guard.conf`:
```sh
IDLE_MINUTES=15
LOCK_ON_HEADSET_OFF=0   # 1 = also quit Signal ~10 s after the headset is taken off
```

- Idle is measured from `/dev/input` directly (the `input` group, as SteamOS sets up), so it
  works whether you're in desktop mode or VR. Constantly chattering sensors (the `als*`
  magnetometer) are ignored.
- The headset check reads the proximity sensor (`vcnl4000`), as documented by
  [steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils#proximity-sensor).
- Only launches from the menu entry are guarded; `flatpak run org.signal.Signal` isn't.

## How secure is it?
The key is only as protected as your wallet. SteamOS's stock `kdewallet` has an
**empty password**, so set one ([wallet](../wallet/#security-set-a-wallet-password)). With a password, you'll be
asked for it once per session when Signal (or another app) first opens the wallet.
Set it in KWalletManager (*kdewallet → Change Password*). The [wallet](../wallet/) installer
makes the wallet close after 4 hours unused.

**What this does and doesn't protect against:** with the wallet locked and Signal not running,
Signal's database can't be decrypted, so someone picking up the headset can't open it. But the
wallet's 4-hour timer counts from its *last use* by any app (Chromium, Claude Desktop, …),
so within that window Signal reopens without a password. It's protection against casual
access, not against someone who can use desktop mode while you're unlocked.
Signal's warning about "experimental" backends mainly concerns GNOME libsecret on
other desktops. On KDE, kwallet6 is the native, intended backend.
