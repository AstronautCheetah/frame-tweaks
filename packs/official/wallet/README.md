---
title: Shared KDE wallet
emoji: 🔐
category: Privacy & security
tier: core
summary: >-
  Password-protect the apps you choose (messages, sign-ins), with one wallet that locks
  itself; shared by desktop mode and VR
what: >-
  Puts the apps you choose behind one password: they ask for the KDE wallet's password before
  they open, and the wallet locks itself again after a while (4 hours unless you change it). The
  same wallet works in desktop mode and VR, with an unlock dialog where you are, a **Lock Wallet**
  button, and a keyring for terminal tools such as `gh`.
why: >-
  Frames are often left without a password or shared with family, yet some apps hold private
  things. This protects just those apps, without locking the whole headset. It also fixes the
  Frame's two sessions (VR and desktop) each having their own wallet, which lose each other's
  logins.
author: Frame Tweaks; launcher approach from lhns/steam-frame-nix
source:
  relation: approach from
  url: https://github.com/lhns/steam-frame-nix
icon: {file: frame-tweaks-lock.png}
run: {label: Unlock}
wallet_apps: [org.kde.kwalletmanager]
changes: >-
  `wallet-unlock`, `wallet-launcher`, `wallet-gate`, `app-timers`, `with-keyring` and a `gh`
  wrapper in `~/.local/bin`; user services `wallet-lock-sync` and `app-timers`; a **Lock Wallet**
  menu entry; `kwalletrc` idle-close setting; KWalletManager (Flathub); rewrites chosen apps'
  menu entries (originals kept in `~/.local/share/frame-tweaks/launcher-originals`)
access: >-
  Talks to KDE Wallet over D-Bus; **closes KDE's own wallet password prompts** (replaced by its
  dialog); reads keyboard, mouse and controller activity and the headset's proximity sensor (for
  app timers); quits apps you set a timer for; moves the GitHub CLI token into the wallet
survives_updates: Yes (everything is in your home folder)
undo: >-
  `./install.sh uninstall wallet` (keeps the wallet itself and KWalletManager; restores the
  original menu entries and the KDE settings it changed)
test:
  offline: true
  keeps: [".config/kwalletrc"]
---
# Shared KDE wallet

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Puts the apps you choose behind one password: they ask for the KDE wallet's password before they open, and the wallet locks itself again after a while (4 hours unless you change it). The same wallet works in desktop mode and VR, with an unlock dialog where you are, a **Lock Wallet** button, and a keyring for terminal tools such as `gh`.

**Why on a Steam Frame:** Frames are often left without a password or shared with family, yet some apps hold private things. This protects just those apps, without locking the whole headset. It also fixes the Frame's two sessions (VR and desktop) each having their own wallet, which lose each other's logins.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install wallet
```

It also installs **KWalletManager** (from Flathub), so you can see what's stored and set a
password. SteamOS has no other wallet window or settings page.

**Then set a wallet password.** SteamOS gives every Frame the same stock wallet, and it opens
**without a password**. Until you set one, what apps "store in the wallet" is only hidden, not
protected. Open KWalletManager → *kdewallet* → *Change Password*.

These apps are set up for you, if installed: KWalletManager, Signal and Claude Desktop. They
use the shared wallet and ask for its password first.

## Use
**Protect an app:** press **🔑 Wallet apps** on this tweak's row in the Frame Tweaks window, find
the app under **Add an app** and press **Protect**. With **Password first** on, it asks for the
wallet password before it opens whenever the wallet is locked. **Close after** can also quit it
when you leave it alone, so the next person who picks up the headset meets the password again.
Signal is protected this way as soon as you install the [Signal tweak](../signal/).

**Unlock:** open a protected app, or use **🔓 Unlock…** on the Wallet apps page. A small "Unlock
wallet" dialog appears on the screen you're using. The wallet then locks itself again after
4 hours, unless you change that or turn **Auto-lock** off (see below).

**Lock:** the **Lock Wallet** entry in the desktop menu and the VR "+" menu, or **🔒 Lock now**
on the Wallet apps page. You can also put it on a controller button: see
[Dictate and Lock Wallet on a controller button](../../../docs/controller-shortcuts.md).

### The Wallet apps page
The **🔑 Wallet apps** button on this tweak's row in the Frame Tweaks window opens a page with:

- **The wallet's state:** open or locked, since when, and when it locks by itself.
- **🔒 Lock now** / **🔓 Unlock…**, and **⏱ Extend timer**, which starts the auto-lock countdown
  again from now.
- **Auto-lock:** ticked by default. Untick it and the wallet stays unlocked until you lock it:
  no countdown, and KDE's own lock after 4 hours unused is turned off too.
- **After unlocking:** − / + between 1 and 24 hours (default 4 hours). The new time counts from
  the next unlock or the next **Extend timer**.
- **Protected** apps, each with:
  - **Password first:** if the wallet is locked, the app asks for the wallet password before it
    opens, and doesn't open without it.
  - **Close after:** quits the app after that long with no keyboard, mouse or controller input
    (5 minutes to 4 hours, or never). Opening it again then needs the wallet again.
  - **Headset off:** also quits it about 10 seconds after you take the headset off (needs a
    Close after time).
  - **Remove:** the app opens the way it did before.
- **Add an app:** every other installed app (Flatpaks, system apps, your own launchers), each
  with a **Protect** button. Electron and Chromium-based apps are detected and told to use the
  wallet; without that they can't keep a sign-in.

**Password first** only controls *opening the app from the menu*. It doesn't encrypt the app's
own files. For Firefox's saved logins, also set Firefox's **Primary Password**, which does.

### From a terminal
```sh
wallet-unlock              # unlock (dialog) if locked
wallet-unlock --status     # locked / unlocked
wallet-unlock --lock       # lock now
wallet-launcher --list                      # protected apps
wallet-launcher org.example.App             # use the shared wallet (--electron for Electron apps)
wallet-launcher --gate org.example.App      # ... and ask for the password first
wallet-launcher --gate --no-shared some-app # password first only, for apps that store nothing in the wallet
wallet-launcher --remove org.example.App    # back to the original menu entry
app-timers --status        # which timed apps are running, and how long you've been idle
```

Close-after timers are saved in `~/.config/frame-tweaks/app-timers.conf`
(`app-id = minutes [headset]`), the auto-lock time in `~/.config/frame-tweaks/wallet.conf`.

**Terminal tools:** `with-keyring CMD` runs a command with the shared wallet as its keyring,
unlocking it first if needed. If the GitHub CLI (`gh`) is installed, the installer adds a `gh`
wrapper in `~/.local/bin` that does this, moves an existing plain-text `gh` token into the
wallet (`gh auth status` then shows "(keyring)"), and points git's existing `gh` credential
helper at the wrapper.

## How it works
**Two sessions, one wallet.** The Frame runs Steam/VR on one D-Bus session bus (the "outer"
one) and the nested Plasma desktop on its own private bus. An app started from the desktop
talks to a *second* wallet service on the private bus: its secrets are invisible to the same
app started from VR, and two services writing the same wallet file can overwrite each other.
`wallet-launcher` fixes this the way [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)
does (`keyring.enable`), without Nix:

- It writes an override menu entry in `~/.local/share/applications/<app-id>.desktop` whose
  command runs through `frame-outer-bus`. For a Flatpak it also lets the app talk to the wallet
  (`--talk-name=org.kde.kwalletd6 --talk-name=org.freedesktop.secrets`). An app's own entry in
  that folder is backed up in `~/.local/share/frame-tweaks/launcher-originals/`. A system app
  gets an override with the same name, which **Remove** deletes again.
- `frame-outer-bus CMD` runs a command on the outer session's D-Bus **and** its runtime folder,
  and keeps the window on the display it was started from. (Switching only the D-Bus address
  makes Flatpak Electron apps such as Signal hang at startup: the outer session's Flatpak portal
  can't find the app.)
- `wallet-gate CMD` (added by **Password first**) runs `wallet-unlock` first and starts the
  app only once the wallet is unlocked.

**The unlock dialog.** The wallet's own password prompt ("KDE Wallet Service") comes from
`ksecretd` on the Steam session's display, so it appears as a floating VR window that may not
take clicks or typing. `wallet-unlock` asks in a normal dialog on your display instead. It
derives the same key KDE's login-time auto-unlock (kwallet-pam) uses, PBKDF2-SHA512 over
`~/.local/share/kwalletd/kdewallet.salt`, and hands it to `ksecretd` over D-Bus, so neither the
password nor the key appears on a command line.

### One unlock route: our dialog, never ksecretd's prompt
| | Window | Behaviour |
|---|---|---|
| ✅ ours | **"Unlock wallet"** | Appears where you are. |
| ❌ ksecretd's | **"KDE Wallet Service"** | Floats in VR. **While it's open, the wallet ignores every other unlock**, so a correct password typed into our dialog looks wrong. |

ksecretd shows its prompt when an app asks for a secret while the wallet is locked without going
through our dialog first. So:
- **Password first** on the apps that use the wallet sends them through our dialog.
- If a ksecretd prompt still appears while the wallet is locked (for example, an app that was
  already running asks again after the auto-lock), the `wallet-lock-sync` service closes it
  (like pressing its ✕) and shows our dialog on the same display. A ksecretd window while the
  wallet is *unlocked* is an "allow this app?" question, and is left alone.

**One auto-lock clock.** Whichever way the wallet gets unlocked, `wallet-lock-sync` restarts the
auto-lock countdown (a systemd timer, `wallet-autolock.timer`) from then. The wallet also closes
after 240 minutes unused (KWallet's own *Close When Idle* setting in `kwalletrc`, which the
installer turns on; set `WALLET_IDLE_MINUTES` when installing to change it).

### KDE 6 gotcha: ksecretd holds the wallet
In KDE 6, `kwalletd6` is only a front end: **`ksecretd`** holds the unlocked wallet. Closing the
wallet in KWalletManager, or KWallet's idle timeout, only closes `kwalletd6`'s view of it;
`ksecretd` stays unlocked, and apps keep getting their secrets without a prompt. So
`wallet-lock-sync` listens for the wallet being closed and then really locks it in `ksecretd`.
**Lock Wallet** and the auto-lock do the same.

## Good to know
- Apps routed to the shared wallet use the outer session's portals and notifications, so some
  desktop integration (such as a tray icon or dark-mode detection) may behave differently.
- An app's own installer (for example another tweak's) may rewrite its menu entry. If **Password
  first** is gone afterwards, turn it on again on the Wallet apps page.
- A **Close after** timer finds apps by their systemd scope (every Flatpak, and other apps
  started from the VR "+" menu or Steam), otherwise by their program. It asks them to quit
  normally.
- "Password refused" although it's right? A ksecretd prompt is probably open in VR. Close it (or
  type the password there), then unlock again.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `wallet-unlock`, `wallet-launcher`, `wallet-gate`, `app-timers`, `with-keyring` and a `gh` wrapper in `~/.local/bin`; user services `wallet-lock-sync` and `app-timers`; a **Lock Wallet** menu entry; `kwalletrc` idle-close setting; KWalletManager (Flathub); rewrites chosen apps' menu entries (originals kept in `~/.local/share/frame-tweaks/launcher-originals`)
- **Unusual access:** Talks to KDE Wallet over D-Bus; **closes KDE's own wallet password prompts** (replaced by its dialog); reads keyboard, mouse and controller activity and the headset's proximity sensor (for app timers); quits apps you set a timer for; moves the GitHub CLI token into the wallet
- **Undo:** `./install.sh uninstall wallet` (keeps the wallet itself and KWalletManager; restores the original menu entries and the KDE settings it changed)
<!-- /generated:changes -->

## Credits
The shared-wallet launcher approach is adapted from [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix) (Apache-2.0), reimplemented without Nix. The unlock key derivation follows KDE's kwallet-pam. The headset's proximity sensor, used by **Headset off**, is documented by [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils#proximity-sensor). D-Bus via [jeepney](https://gitlab.com/takluyver/jeepney) (MIT). See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status wallet` · Remove: `./install.sh uninstall wallet`
