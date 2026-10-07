# Steam Frame Tweaks

**Make the Valve Steam Frame's desktop mode a better place to work.** Pick from a dozen
self-contained tweaks: local dictation, the arrow keys the Steam keyboard lacks, phone
mirroring, a shared and lockable KDE wallet, protected Signal and Firefox, NordVPN that
survives updates, and Claude Desktop. Install them from a checklist.

- **Nothing in the system partition.** Everything goes into your home folder, so SteamOS
  updates don't undo it, and nothing needs `sudo` or `steamos-readonly disable`.
- **Pick and choose.** Every tweak installs, checks and removes on its own; dependencies are
  added automatically.
- **Safe to re-run.** Installing again repairs; `status` tells you what's healthy.

## Quick start

In desktop mode, open **Konsole** and run:

```sh
git clone https://github.com/AstronautCheetah/steam-frame-tweaks ~/steam-frame-tweaks
~/steam-frame-tweaks/get.sh
```

<!-- once public:  curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/steam-frame-tweaks/main/get.sh | bash -->

A checklist opens: tick what you want and press OK. It also adds **Steam Frame Tweaks** to
the app menu, so you can come back later to add, repair or remove tweaks.

Some tweaks use [Homebrew](https://brew.sh) (dictation, phone mirror). Install it first if you
want those.

## The tweaks

| | Tweak | What you get |
|---|---|---|
| ⌨️ | [**Dictation**](dictation/) | Speech-to-text that runs on the Frame's GPU (Whisper, ~3.5 s for 11 s of speech). One shortcut to start/stop; the text is typed into the focused app, copied, and logged. |
| ⌨️ | [**Arrow Pad**](arrowpad/) | Floating pad with arrows, Home/End, PgUp/PgDn, F-keys, one-shot Ctrl/Alt/Shift, clipboard keys and a 🎤 button. Never steals focus. |
| ⌨️ | [**Full Keyboard**](full-keyboard/) | TaiKeid's full-size VR keyboard for the dashboard and desktop (checksum-verified install). |
| 🖱️ | [**Mouse cursor fix**](cursor/) | Makes the pointer visible in desktop mode. |
| 📱 | [**Phone Mirror**](adb-scrcpy/) | Mirror and control your Android phone (scrcpy over wireless adb, with an aarch64 adb). Finds the phone's changing port automatically. |
| 🔐 | [**Shared KDE wallet**](wallet/) | One wallet for desktop mode *and* VR, an unlock dialog that works on the desktop, 4-hour auto-lock, password-gated apps, and CLI credentials (`gh`) kept out of plain-text files. |
| 🔐 | [**Signal hardening**](signal/) | Signal's database key in the wallet instead of plain text; Signal quits after 15 minutes idle, and reopening needs the wallet password. |
| 🌐 | [**NordVPN (WireGuard)**](nordvpn/) | NordVPN servers in several countries as built-in network connections, with a tray icon. Survives SteamOS updates. |
| 🕵️ | [**Firefox privacy**](firefox/) | Firefox's strongest anti-fingerprinting (the Tor Browser approach), letterboxing, WebRTC limits, daily re-randomization. |
| 🤖 | [**Claude Desktop**](claude-desktop/) | Anthropic's official Linux arm64 beta, installed and updated without apt. |
| 🛠️ | [**Tools**](tools/) | `restart-plasmashell`: bring the taskbar and tray back after a crash. |

Each folder's README covers usage, settings, how it works, and the gotchas we hit.

## Using the installer

```text
./install.sh                    checklist (desktop mode), or help + status (terminal)
./install.sh install signal     install (adds dependencies: wallet)
./install.sh install all
./install.sh status             health check, changes nothing
./install.sh update             git pull + re-run the installer of everything installed
./install.sh uninstall nordvpn  remove one
./install.sh list
```

```text
$ ./install.sh status
  ✔ dictation       dictate ready (2 model(s))
  ✔ wallet          wallet locked; 5 app launcher(s) routed/gated
  ✔ signal          key in wallet; idle guard on (IDLE_MINUTES=15)
  ! nordvpn         not set up yet (run: nordvpn-wg setup)
  · claude-desktop  not installed
```

Removing a tweak keeps your settings and data (it says what it kept). Settings live in
`~/.config` (`dictate.conf`, `signal-guard.conf`, `phone.conf`, `nordvpn-wg/`, …).

## Things worth knowing about the Frame

- **Desktop mode is nested.** Plasma runs inside the Steam/VR session with its own D-Bus and
  `XDG_RUNTIME_DIR` (`/run/user/$UID/nested_plasma`). Apps started from the desktop, from
  shortcuts and from VR can see different environments, wallets and keyrings. Many tweaks
  here exist because of this; see [wallet](wallet/).
- **Anything installed into `/usr`** (via `steamos-readonly disable` + pacman) disappears at the
  next SteamOS update. Prefer home-folder installs, Flatpaks, or config in `/etc` (as
  [nordvpn](nordvpn/) does).
- **SteamOS's stock KDE wallet has no password.** Set one; see [SECURITY.md](SECURITY.md).
- **Steam's on-screen keyboard:** hold **Shift** for ←/→.
  X11-only on-screen keyboards (e.g. CoreKeyboard) don't work under the Wayland desktop.
- **Closing desktop mode can half-tear it down.** Steam may delete the nested session's runtime
  folder while KWin keeps running, so new apps fail with "Failed to initialize Wayland". Exit
  and reopen desktop mode, or reboot.
- **Vulkan apps** can crash in the Gamescope WSI layer; try `DISABLE_GAMESCOPE_WSI=1`.

## How this compares

Other Frame projects, and how this one relates:

| Project | Approach | Overlap |
|---|---|---|
| [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix) | Nix Home Manager modules, declarative | Two-session fixes, shared wallet (our [wallet](wallet/) adapts its launcher approach without Nix), VR keyboard patches |
| [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils) | `setup.sh` + app installers | Cursor fix (adopted from here, credited), Full Keyboard installer |
| [TaiKeid/steam-frame-full-keyboard](https://github.com/TaiKeid/steam-frame-full-keyboard) | Native VR keyboard | Installed by our `full-keyboard` |
| [techieyann/frame-voice](https://github.com/techieyann/frame-voice), [groffta/whisper-frame](https://github.com/groffta/whisper-frame), [gripspeak](https://github.com/gripspeak/gripspeak) | Dictation apps | Alternatives to our [dictation](dictation/) |

**Choose this repo if** you want a checklist installer, no Nix, and the security, privacy and
connectivity pieces (wallet, Signal, Firefox, NordVPN) alongside input and quality-of-life fixes.

## Contributing, security, license

- New tweaks are folders with `install.sh` / `status.sh` / `uninstall.sh`; see
  [CONTRIBUTING.md](CONTRIBUTING.md).
- What touches secrets, and the threat model: [SECURITY.md](SECURITY.md).
- [MIT](LICENSE). Changes: [CHANGELOG.md](CHANGELOG.md).

Built on SteamOS 0.4.5 (build 20261006) on a Steam Frame. Tested on one headset so far:
reports from others are welcome.
