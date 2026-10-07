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
wallet-unlock            # dialog if locked; then auto-locks after WALLET_LOCK_HOURS (4)
wallet-unlock --status   # locked / unlocked
wallet-unlock --lock     # lock now
```

It derives the same key KDE's login auto-unlock (kwallet-pam) uses (PBKDF2-SHA512 over
`~/.local/share/kwalletd/kdewallet.salt`) and passes it to `ksecretd`'s `pamOpen` over
D-Bus (jeepney), so neither password nor key appears on a command line. The Signal
launcher runs it before Signal starts.

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

---
Check: `./install.sh status wallet` · Remove: `./install.sh uninstall wallet`
