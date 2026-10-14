---
title: "Signal: key in the wallet"
emoji: 🔐
category: Privacy & security
tier: extras
summary: >-
  Signal's database key in the wallet instead of plain text (an existing plain-text key is moved
  over)
what: >-
  Signal's database key in the wallet instead of plain text (an existing plain-text key is moved
  over). Password first and Close after are set in Wallet apps.
why: >-
  A headset gets passed around: shared with family, often without a SteamOS login password.
  Flathub Signal otherwise keeps its key in plain text.
author: Frame Tweaks
depends: [wallet]
icon: {flatpak: org.signal.Signal, theme: dialog-messages}
run: {label: Open}
wallet_apps: [org.signal.Signal]
changes: >-
  Signal's menu entry (Wallet apps: password first, Close-after timer), a Flatpak override for
  Signal, Signal's `config.json`
access: >-
  Asks for the wallet password first; quits Signal when idle; key in the wallet
survives_updates: Yes (everything is in your home folder)
undo: >-
  `./install.sh uninstall signal` (Signal keeps using the wallet: switching back would lock you
  out of its data)
---
# Signal: key in the wallet

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Signal's database key in the wallet instead of plain text (an existing plain-text key is moved over). Password first and Close after are set in Wallet apps.

**Why on a Steam Frame:** A headset gets passed around: shared with family, often without a SteamOS login password. Flathub Signal otherwise keeps its key in plain text.
<!-- /generated:intro -->

The Flathub build of Signal Desktop asks on every launch whether to use the
**plaintext** password store. Choosing it leaves the key to your message database
unencrypted on disk. This tweak makes it use **KDE Wallet** instead:


```sh
./install.sh install signal
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

## Password first and idle lock (Wallet apps)
Signal Desktop has no lock of its own (Signal has declined to add one), so Signal gets the
wallet's standard protections, set in the installer window's **🔑 Wallet apps** page:

- **Password first:** if the wallet is locked, you get the
  [`wallet-unlock`](../wallet/#unlocking-from-the-desktop-wallet-unlock) password dialog, and
  Signal doesn't start without it.
- **Close after 15 minutes** without keyboard, mouse or controller input (`app-timers`), so
  reopening Signal needs the wallet again. **Headset off** can also quit it ~10 s after the
  headset is taken off. Both are adjustable there, like for any other app.

These replaced `signal-guard`, which did both for Signal alone; reinstalling the Signal tweak
switches over and carries its settings (`~/.config/signal-guard.conf`) into the timer.

## How secure is it?
The key is only as protected as your wallet. SteamOS's stock `kdewallet` has an
**empty password**, so set one ([wallet](../wallet/#security-set-a-wallet-password)). With a password, you'll be
asked for it once per session when Signal (or another app) first opens the wallet.
Set it in KWalletManager (*kdewallet → Change Password*). The [wallet](../wallet/) installer
makes the wallet close after 4 hours unused.

**What this does and doesn't protect against:** with the wallet locked and Signal not running,
Signal's database can't be decrypted, so someone picking up the headset can't open it. But the
wallet stays unlocked for 4 hours after you unlock it, so within that window Signal
reopens without a password (`wallet-unlock --lock` locks it early). It's protection against casual
access, not against someone who can use desktop mode while you're unlocked.
Signal's warning about "experimental" backends mainly concerns GNOME libsecret on
other desktops. On KDE, kwallet6 is the native, intended backend.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** Signal's menu entry (Wallet apps: password first, Close-after timer), a Flatpak override for Signal, Signal's `config.json`
- **Unusual access:** Asks for the wallet password first; quits Signal when idle; key in the wallet
- **Undo:** `./install.sh uninstall signal` (Signal keeps using the wallet: switching back would lock you out of its data)
<!-- /generated:changes -->

## Credits
Signal is a trademark of Signal Technology Foundation; not affiliated. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status signal` · Remove: `./install.sh uninstall signal`
