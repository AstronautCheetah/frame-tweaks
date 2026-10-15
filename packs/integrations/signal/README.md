---
title: "Signal: key in the wallet"
emoji: 🔐
category: Privacy & security
tier: extras
summary: >-
  Signal's database key in the wallet instead of plain text (an existing plain-text key is moved
  over)
what: >-
  Signal Desktop keeps the key to your message database in the KDE wallet instead of a
  plain-text file (an existing plain-text key is moved over), and asks for the wallet password
  before it opens.
why: >-
  A headset gets passed around, often without a SteamOS login password, and Flathub's Signal
  otherwise keeps its database key in plain text.
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
Signal Desktop keeps the key to your message database in the KDE wallet instead of a plain-text file (an existing plain-text key is moved over), and asks for the wallet password before it opens.

**Why on a Steam Frame:** A headset gets passed around, often without a SteamOS login password, and Flathub's Signal otherwise keeps its database key in plain text.
<!-- /generated:intro -->

## Install
Install Signal from Flathub first (Discover, or `flatpak install flathub org.signal.Signal`).
Then tick it in the Frame Tweaks window, or:

```sh
./install.sh install signal
```

It installs the [Shared KDE wallet](../../core/wallet/) tweak too, if needed. If Signal already has a
plain-text key, the installer moves it into the wallet for you: Signal does this by itself over
two launches, so the installer starts and closes Signal twice (about 20 seconds each), then
checks the result. To check again later:

```sh
packs/integrations/signal/check   # "OK: database key is encrypted via kwallet6; ..."
```

Set a wallet password if you haven't yet (KWalletManager → *kdewallet* → *Change Password*):
the key is only as safe as the wallet, and SteamOS's stock wallet has none.

## Use
Open Signal as usual, from the desktop or the VR "+" menu. Both use the same wallet. If the
wallet is locked, a small "Unlock wallet" dialog asks for its password first, and Signal
doesn't open without it.

Signal Desktop has no lock of its own, so it gets the wallet's protections instead. Change them
on the **🔑 Wallet apps** page (the button on the Shared KDE wallet row in the Frame Tweaks
window):

- **Password first:** on.
- **Close after:** Signal quits after **15 minutes** (unless you had already set a time) with
  no keyboard, mouse or controller input, so opening it again needs the wallet again.
- **Headset off:** off by default; turn it on to also quit Signal about 10 seconds after the
  headset is taken off.

## How it works
Flathub's Signal asks at every start whether to keep its database key in plain text. This tweak
sets `SIGNAL_PASSWORD_STORE=kwallet6` as a per-user Flatpak override (the same as doing it in
Flatseal), so Signal stops asking and keeps the key in KDE Wallet. It also gives Signal a
[wallet launcher](../../core/wallet/#how-it-works) with **Password first**, so it uses the same wallet
from the desktop and from VR.

Signal's warning about "experimental" password stores is mainly about GNOME's keyring on other
desktops. On KDE, kwallet6 is the native one.

## Good to know
- **What it protects against:** with the wallet locked and Signal closed, Signal's database
  can't be decrypted, so someone who picks up the headset can't read your messages. But while
  the wallet is unlocked (4 hours after you unlock it, unless you change that), Signal opens
  without a password. Lock the wallet early with **Lock Wallet**. This protects against casual
  access, not against someone using the headset while the wallet is unlocked.
- **Uninstalling keeps the wallet setting.** Signal's key now lives in the wallet; switching
  Signal back to plain text would lock you out of your messages. Password first and the Close
  after timer also stay: change them on the Wallet apps page.

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
