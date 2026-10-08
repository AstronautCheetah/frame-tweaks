# Steam Frame Tweaks

[![CI](https://github.com/AstronautCheetah/steam-frame-tweaks/actions/workflows/ci.yml/badge.svg)](https://github.com/AstronautCheetah/steam-frame-tweaks/actions/workflows/ci.yml)

**Make the Valve Steam Frame's desktop mode a better place to work.** Pick from a dozen
self-contained tweaks: local dictation, the arrow keys the Steam keyboard lacks, Android
mirroring, a shared and lockable KDE wallet, protected Signal and Firefox, NordVPN that
survives updates, and Claude Desktop. Install them from a checklist.

- **Nothing in the system partition.** Everything goes into your home folder, so SteamOS
  updates don't undo it, and nothing needs `steamos-readonly disable` (only Homebrew's
  one-time setup asks for sudo).
- **Pick and choose.** Every tweak installs, checks and removes on its own; dependencies are
  added automatically.
- **Safe to re-run.** Installing again repairs; `status` tells you what's healthy.

## Quick start

In desktop mode, open **Konsole** and run:

```sh
curl -fsSL https://raw.githubusercontent.com/AstronautCheetah/steam-frame-tweaks/main/get.sh | bash
```

A checklist opens: tick what you want and press OK. It also adds **Steam Frame Tweaks** to
the app menu (desktop and VR "+" menu), so you can come back later to add, repair or remove
tweaks.

<details><summary>Prefer to look before you run?</summary>

```sh
git clone https://github.com/AstronautCheetah/steam-frame-tweaks ~/steam-frame-tweaks
less ~/steam-frame-tweaks/get.sh        # read it
~/steam-frame-tweaks/get.sh
```
</details>

Tweaks that need [Homebrew](https://brew.sh) (dictation, Android mirror) offer to install it
if it's missing. It needs your sudo password once; if you've never set one, run `passwd` first.

## The tweaks

| | Tweak | What you get | Why (on the Frame) |
|---|---|---|---|
| ⌨️ | [**Dictation**](dictation/) | Speech-to-text that runs on the Frame's GPU (Whisper, ~3.5 s for 11 s of speech). One shortcut or the Arrow Pad's 🎤 to start/stop; the text is typed into the focused app, copied, and logged. | Typing on a VR keyboard with controller lasers is slow. The Frame's Adreno GPU is fast enough to transcribe locally, so nothing leaves the headset. |
| 🎙️ | [**whisper-frame**](whisper-frame/) | groffta's dictation: hold the headset's Select button, or the mic under any floating window. Installed from upstream; shares dictation's model. | Dictate without menus or the desktop, straight into the window you're looking at in VR. |
| ⌨️ | [**Arrow Pad**](arrowpad/) | Floating pad with arrows, Home/End, PgUp/PgDn, F-keys, one-shot Ctrl/Alt/Shift, clipboard keys and a 🎤 button. Opens in desktop mode or as its own VR window; never steals focus. | Steam's on-screen keyboard has no up/down arrows, Esc, Ctrl or F-keys, and most on-screen keyboards don't work under the Frame's Wayland desktop. |
| ⌨️ | [**Full Keyboard**](full-keyboard/) | TaiKeid's full-size VR keyboard for the dashboard and desktop (checksum-verified install). | The best in-VR keyboard so far; this installs and updates it with the rest. |
| 🌀 | [**Curved world windows**](curvature/) | Windows you float into the world start curved, like the dashboard; Toggle Curvature still works. | SteamVR has no setting for it (world windows always start flat), so a tiny dashboard patch presses the toggle for you. Restart SteamVR once after installing. |
| 🖱️ | [**Mouse cursor fix**](cursor/) | Makes the pointer visible in desktop mode. | KWin draws the pointer on a hardware plane that the headset's view doesn't show, so in desktop mode the mouse moves invisibly. |
| 📋 | [**Shared clipboard**](clipboard/) | Copy in a floating VR window, paste in the desktop, and back. | The Frame's VR session and its nested desktop each have their own clipboard. This runs [clipboard-sync](https://github.com/dnut/clipboard-sync), built from upstream, as steam-frame-nix does. |
| 📱 | [**Android Mirror**](adb-scrcpy/) | Mirror and control your Android phone in a desktop window (scrcpy over wireless adb). Finds the phone's changing port automatically. | Use your phone without taking the headset off. Google ships `adb` only for x86, so this installs an aarch64 build that runs on the Frame. |
| 🔐 | [**Shared KDE wallet**](wallet/) | One wallet for desktop mode *and* VR, an unlock dialog that works on the desktop, 4-hour auto-lock, a **Lock Wallet** button, closing that really locks, password-gated apps, and CLI credentials (`gh`) kept out of plain-text files. | The Frame runs two sessions (VR and a nested desktop) with separate D-Bus buses, so apps get two wallets that overwrite each other. The VR-side password prompt floats in VR, and terminal tools find no keyring at all. SteamOS's stock wallet has no password. |
| 🔐 | [**Signal hardening**](signal/) | Signal's database key in the wallet instead of plain text; Signal quits after 15 minutes idle, and reopening needs the wallet password. | A headset gets passed around: shared with family, often without a SteamOS login password. Flathub Signal otherwise keeps its key in plain text. |
| 🌐 | [**NordVPN (WireGuard)**](nordvpn/) | NordVPN servers in several countries as built-in network connections, with a tray icon. Survives SteamOS updates. | The usual NordVPN install goes into `/usr`, which every SteamOS update wipes, and the Frame's desktop has no network applet to switch VPNs. |
| 🕵️ | [**Firefox privacy**](firefox/) | Firefox's strongest anti-fingerprinting (the Tor Browser approach), letterboxing, WebRTC limits, daily re-randomization. | The Frame's hardware (Adreno GPU, VR-desktop screen size, touch input) is rare among browsers, so it's easy to fingerprint. |
| 🧑‍💻 | [**VSCodium**](vscodium/) | VS Code without telemetry, from Flathub. | Coding on the headset: Flathub has the aarch64 build; pairs with Arrow Pad and dictation. |
| 🤖 | [**Claude Code**](claude-code/) (command line) | Anthropic's coding agent in the terminal (`claude`), via Anthropic's own installer. | The native installer runs without root on arm64 and updates itself, so SteamOS updates leave it alone. |
| 🤖 | [**Claude Desktop**](claude-desktop/) | Anthropic's official Linux arm64 beta, installed and updated without apt. | It's packaged as a `.deb` for Ubuntu/Debian. SteamOS has no apt and a read-only root, so this unpacks the arm64 build into your home folder. |
| 🛠️ | [**Tools**](tools/) | `restart-plasmashell`: bring the taskbar and tray back after a crash. | In the Frame's nested desktop, nothing restarts a crashed taskbar automatically, and it has to be relaunched inside that session. |

Each folder's README covers usage, settings, how it works, and the gotchas we hit.

## Using the installer

**Steam Frame Tweaks** in the app menu (desktop or VR "+" menu) opens the installer window.
Tweaks are grouped by category (convenience first, developer tools last), each with its live
status and a link to the project it comes from. **▶ Open / Dictate / Unlock / Restart…** runs
what each tweak provides (**Help** where there's nothing to launch). Tick to install, untick to
remove, **click a row** for details (what it is, why it's included, who made it, its README), **Hide** rows you
don't need (never removed) and **Show hidden** to bring them back. whisper-frame starts hidden
while its window mic costs VR performance. It uses
PyQt6, set up on first use (shared with Arrow Pad); without it you get a simple checklist.

```text
./install.sh                    installer window (desktop mode), or help + status (terminal)
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
  ✔ claude-code     Claude Code 2.1.293 (run: claude)
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

## Credits

This builds on [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix) (shared-wallet
launchers, two-session know-how), [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils)
(cursor fix, proximity sensor), [TaiKeid/steam-frame-full-keyboard](https://github.com/TaiKeid/steam-frame-full-keyboard)
(Arrow Pad style and haptics) and [techieyann/frame-voice](https://github.com/techieyann/frame-voice)
(installer shape), and on whisper.cpp, scrcpy, ydotool, KDE and others. Details and licenses:
[CREDITS.md](CREDITS.md). Not affiliated with Valve or any vendor named here.

## Contributing, security, license

- New tweaks are folders with `install.sh` / `status.sh` / `uninstall.sh`; see
  [CONTRIBUTING.md](CONTRIBUTING.md).
- What touches secrets, and the threat model: [SECURITY.md](SECURITY.md).
- [MIT](LICENSE). Changes: [CHANGELOG.md](CHANGELOG.md).

Built on SteamOS 0.4.5 (build 20261006) on a Steam Frame. Tested on one headset so far:
reports from others are welcome.
