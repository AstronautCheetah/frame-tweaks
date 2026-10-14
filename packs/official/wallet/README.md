---
title: Shared KDE wallet
emoji: 🔐
category: Privacy & security
tier: core
summary: >-
  One wallet for desktop mode and VR, desktop unlock dialog, 4-hour auto-lock, keyring for CLI
  tools
what: >-
  One wallet for desktop mode *and* VR, an unlock dialog that works on the desktop, 4-hour
  auto-lock, a **Lock Wallet** button, closing that really locks, password-gated apps, and CLI
  credentials (`gh`) kept out of plain-text files.
why: >-
  The Frame runs two sessions (VR and a nested desktop) with separate D-Bus buses, so apps get
  two wallets that overwrite each other. The VR-side password prompt floats in VR, and terminal
  tools find no keyring at all. SteamOS's stock wallet has no password.
author: Frame Tweaks; launcher approach from lhns/steam-frame-nix
source:
  relation: approach from
  url: https://github.com/lhns/steam-frame-nix
icon: {file: frame-tweaks-lock.png}
run: {label: Unlock}
wallet_apps: [org.kde.kwalletmanager]
changes: >-
  `wallet-unlock`, `wallet-launcher`, `wallet-gate`, user service `wallet-lock-sync`,
  `kwalletrc` setting; rewrites chosen apps' menu entries (originals kept in
  `~/.local/share/frame-tweaks/launcher-originals`)
access: >-
  Talks to KDE Wallet over D-Bus; **closes KDE's own wallet password prompts** (replaced by its
  dialog); moves the GitHub CLI token into the wallet
survives_updates: Yes (everything is in your home folder)
undo: >-
  `./install.sh uninstall wallet` (keeps the wallet itself and KWalletManager; restores the KDE
  settings it changed)
test:
  offline: true
  keeps: [".config/kwalletrc"]
---
# Wallet: one KDE wallet for both sessions

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
One wallet for desktop mode *and* VR, an unlock dialog that works on the desktop, 4-hour auto-lock, a **Lock Wallet** button, closing that really locks, password-gated apps, and CLI credentials (`gh`) kept out of plain-text files.

**Why on a Steam Frame:** The Frame runs two sessions (VR and a nested desktop) with separate D-Bus buses, so apps get two wallets that overwrite each other. The VR-side password prompt floats in VR, and terminal tools find no keyring at all. SteamOS's stock wallet has no password.
<!-- /generated:intro -->

The Frame runs two sessions at once: Steam/VR on the outer D-Bus and the nested
Plasma desktop on its own private bus. An app started from the desktop talks to a
**second** `kwalletd6` on the private bus. Its secrets are invisible to the same app
started from VR, and two daemons writing the same wallet file can overwrite each
other. This follows [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s
launcher approach (`keyring.enable`), without needing Nix:


**In the installer window: 🔑 Wallet apps** (the button on this tweak's row) lists the protected apps, each with a
**Password first** switch and **Remove**, and every other installed app (Flatpaks from any
source, such as Discover; system apps; your own launchers) with a **Protect** button. Electron
and Chromium-based apps are detected and told to use the wallet.

**Close after** (per protected app) quits the app after that long with no keyboard, mouse or
controller input, so opening it again needs the wallet again (this replaced Signal's own guard).
**Headset off** also quits it ~10 s after the headset is taken off (the proximity sensor, as
documented by [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils#proximity-sensor)). The `app-timers` user service does it; timers are in `~/.config/frame-tweaks/app-timers.conf`
(`app-id = minutes [headset]`). Apps are
found by their systemd scope (every Flatpak; other apps started from the VR "+" menu or Steam),
else by their program (other apps started from desktop mode). `app-timers --status` shows what
it sees.

```sh
./install.sh install wallet
wallet-launcher --list            # apps currently routed to the shared wallet
wallet-launcher org.example.App   # add one (--electron adds --password-store=kwallet6)
wallet-launcher --remove org.example.App
```

- **`wallet-launcher`** writes an override menu entry (`~/.local/share/applications/<id>.desktop`)
  whose command runs through `frame-outer-bus`. For Flatpaks it also adds
  `--talk-name=org.kde.kwalletd6 --talk-name=org.freedesktop.secrets`. Host-app
  originals are backed up in `~/.local/share/frame-tweaks/launcher-originals/`. A system app
  (`/usr/share/applications`, read-only) gets an override of the same name, which `--remove`
  deletes so the system entry shows again.
- **`frame-outer-bus <cmd>`** runs a command on the outer session's D-Bus **and** runtime dir.
  It keeps the window on the display it was launched from by pinning `WAYLAND_DISPLAY`
  as an absolute path.
- **KWalletManager** (Flathub) is installed and routed to the shared wallet, so you can
  see what's stored and set a password. SteamOS has no wallet GUI or settings page.

Installed by default for: KWalletManager, Signal and Claude Desktop (when present).

## Password-gating other apps: `--gate`
`wallet-launcher --gate <app-id>` makes the app's menu entry run **`wallet-gate`** first: if
the wallet is locked you get the `wallet-unlock` dialog, and the app doesn't start without
the password. Add `--no-shared` for apps that don't store anything in the wallet themselves
(their bus stays as it is):

```sh
wallet-launcher --gate --no-shared org.mozilla.firefox android-mirror
```

A gate only controls *launching from the menu*. It doesn't encrypt the app's data. For
Firefox's saved logins, also set Firefox's **Primary Password**, which actually encrypts them.
Re-running an app's own installer (e.g. `adb-scrcpy`) rewrites its entry, so re-apply the gate.

## Unlocking from the desktop: `wallet-unlock`
The shared wallet's own password prompt comes from `ksecretd` on the Steam session's
display, so it appears as a **floating VR window**, which may not take clicks or typing.
`wallet-unlock` asks in a normal dialog on *your* display instead:

```sh
wallet-unlock            # dialog if locked; then auto-locks after 4 h (set on the Wallet apps page)
wallet-unlock --status   # locked / unlocked
wallet-unlock --lock     # lock now
```

It derives the same key KDE's login auto-unlock (kwallet-pam) uses (PBKDF2-SHA512 over
`~/.local/share/kwalletd/kdewallet.salt`) and passes it to `ksecretd`'s `pamOpen` over
D-Bus (jeepney), so neither password nor key appears on a command line. The Signal
launcher runs it before Signal starts.

## One unlock route: our dialog, never ksecretd's prompt
There are two password prompts, and only one works reliably:

| | Window | Behaviour |
|---|---|---|
| ✅ ours | **"Unlock wallet"** (`kdialog`) | Appears where you are; unlocks with the password-derived key. |
| ❌ ksecretd's | **"KDE Wallet Service"** (`ksecretd`) | Floats in VR. **While it's open, ksecretd ignores every other unlock**, so a correct password typed into our dialog looks wrong, and a forgotten one blocks the wallet. |

ksecretd prompts when an app asks for a secret while the wallet is locked without going
through our gate first. So:
- **Routes closed:** Signal, KWalletManager and Claude Desktop open through our dialog
  (`wallet-launcher --gate`), like Firefox and Android Mirror.
- **Prompt replaced:** if a ksecretd prompt still appears while the wallet is locked (e.g. an
  already-running app asking again after the auto-lock), `wallet-lock-sync` closes it (like
  its ✕, which ksecretd treats as Cancel) and shows our dialog on the same display. A ksecretd
  window on an *unlocked* wallet is an "allow this app?" question and is left alone.
- **One auto-lock clock:** whichever way the wallet gets unlocked, the 4-hour auto-lock
  restarts from then.

## "Closed" means locked: `wallet-lock-sync`
Closing the wallet in KWalletManager (or KWallet's idle timeout) only closes `kwalletd6`'s view
of it; `ksecretd` stays unlocked, and apps such as Signal keep getting their secrets without a
prompt. The `wallet-lock-sync` user service (`wallet-unlock --watch`) listens for kwalletd6's
`walletClosed` signal and then really locks `ksecretd`. The **Lock Wallet** menu entry
(`wallet-unlock --lock`) locks it on demand.

## Command-line tools: `with-keyring`
Terminals in desktop mode are on the nested desktop's D-Bus, which has **no Secret
Service**, so CLI tools that use the system keyring silently fall back to plain-text files.
`gh auth login`, for example, prints "Authentication credentials saved in plain text" and
writes the token to `~/.config/gh/hosts.yml`.

`with-keyring CMD` runs a command against the shared wallet on the outer bus (unlocking it
with the desktop dialog if needed). The installer adds a `~/.local/bin/gh` wrapper that uses
it, points git's credential helper at the wrapper, and moves an existing plain-text gh token
into the wallet (`gh auth status` then shows "(keyring)").

## Auto-lock (4 hours)
`wallet-unlock` starts a transient systemd timer (`wallet-autolock.timer`) that runs
`wallet-unlock --lock` 4 hours after you unlock, via the Secret Service `Lock` call plus
closing kwalletd6's handle. KWallet's own *Close When Idle* setting (also set, 240 min)
isn't enough on its own (see below).

## KDE 6 gotcha: `ksecretd` holds the wallet
In KDE Frameworks 6, `kwalletd6` is a front end and **`ksecretd`** keeps the actual
unlocked state. Closing the wallet through `kwalletd6` (`close(…, force)`), or even
restarting `kwalletd6`, leaves `ksecretd` unlocked, so apps reopen the wallet silently.
A wallet unlocked before you set a password also stays unlocked until `ksecretd` restarts or
is locked through `org.freedesktop.Secret.Service.Lock`. `ksecretd` is D-Bus-activatable
only under the name `org.kde.secretservicecompat`.
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

**On a controller button:** see [Dictate and Lock Wallet on a controller button](../../../docs/controller-shortcuts.md).

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `wallet-unlock`, `wallet-launcher`, `wallet-gate`, user service `wallet-lock-sync`, `kwalletrc` setting; rewrites chosen apps' menu entries (originals kept in `~/.local/share/frame-tweaks/launcher-originals`)
- **Unusual access:** Talks to KDE Wallet over D-Bus; **closes KDE's own wallet password prompts** (replaced by its dialog); moves the GitHub CLI token into the wallet
- **Undo:** `./install.sh uninstall wallet` (keeps the wallet itself and KWalletManager; restores the KDE settings it changed)
<!-- /generated:changes -->

## Credits
The shared-wallet launcher approach is adapted from [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix) (Apache-2.0), reimplemented without Nix. The unlock key derivation follows KDE's kwallet-pam. D-Bus via [jeepney](https://gitlab.com/takluyver/jeepney) (MIT). See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status wallet` · Remove: `./install.sh uninstall wallet`
