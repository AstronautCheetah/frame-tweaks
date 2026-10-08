# Credits

This project stands on other people's work. Ideas we adapted are credited here and in the
README of the tweak that uses them; software we install or call keeps its own license.

## Steam Frame projects we learned from

| Project | License | What we took |
|---|---|---|
| [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix) | Apache-2.0 | The **shared clipboard** (its `clipboardSync`: run dnut/clipboard-sync from the desktop session; our [clipboard](clipboard/)). The **shared-wallet launcher** approach (`keyring.enable`: run wallet-using apps on the outer D-Bus so desktop mode and VR share one `kwalletd6`), which our [wallet](wallet/) reimplements without Nix. Much of our understanding of the Frame's **two sessions**: Steam's "+" menu (icons only from hicolor; rescans on the applications folder's mtime; a `~/.local/share/applications` entry replaces the Flatpak one), the portal setup. Ideas for the [Arrow Pad](arrowpad/): one-shot/locked modifiers and an F-key layer, from its VR keyboard patches. The [curved world windows](curvature/) approach: SteamVR's dashboard DevTools port set only while SteamVR runs, and how the dashboard's curvature component works (its window-curvature and steamvr-debugger modules). No code copied. |
| [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils) | none stated | The **mouse cursor fix** (`KWIN_FORCE_SW_CURSOR=1`, our [cursor](cursor/)), and the documentation of the **proximity sensor** used by [signal-guard](signal/)'s headset-off option. The checksum-then-run pattern of our [full-keyboard](full-keyboard/) installer follows its `install-full-keyboard.sh`. No code copied. |
| [TaiKeid/steam-frame-full-keyboard](https://github.com/TaiKeid/steam-frame-full-keyboard) | MIT | Installed by [full-keyboard](full-keyboard/). The [Arrow Pad](arrowpad/)'s look and feel follows it: the **Graphite theme colours**, the toolbar (pin, recenter, smaller/larger), copy/paste buttons, relaunch-to-toggle, and its **haptic feedback values** (hover 4 ms / 10 % / 240 Hz, press 25 ms / 100 % / 150 Hz). |
| [techieyann/frame-voice](https://github.com/techieyann/frame-voice) | MIT | The shape of our installer: a one-line `get.sh` bootstrap, a graphical installer, and a documented uninstall. No code copied. |
| [groffta/whisper-frame](https://github.com/groffta/whisper-frame) | MIT | Installed by [whisper-frame](whisper-frame/) from its upstream releases (we add a SteamVR-restart fix). Our [dictation](dictation/) shares its Whisper model and bundled whisper-cli. |
| [gripspeak](https://github.com/gripspeak/gripspeak) | – | Not used; an alternative worth knowing. |

The cursor fix was popularised by Cas and Chary XR's video *Steam Frame: 10 Things To Do
FIRST*, which credits **ThrillSeeker**.

## Software the tweaks install or use

| Software | License | Used by |
|---|---|---|
| [dnut/clipboard-sync](https://github.com/dnut/clipboard-sync) | see upstream | clipboard (built from upstream source, not bundled; approach from steam-frame-nix's `clipboardSync`) |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) and OpenAI's Whisper models | MIT | dictation (via Homebrew; models from Hugging Face) |
| [ydotool](https://github.com/ReimuNotMoe/ydotool) | AGPL-3.0 | dictation, Arrow Pad (Arch Linux ARM package, not modified) |
| [scrcpy](https://github.com/Genymobile/scrcpy) | Apache-2.0 | Android Mirror (Homebrew) |
| Android `adb` (android-tools) | Apache-2.0 | Android Mirror (Arch Linux ARM package) |
| [Arch Linux ARM](https://archlinuxarm.org) packages | various | adb, ydotool and libraries |
| [Homebrew](https://brew.sh) | BSD-2-Clause | [homebrew](homebrew/) row; installs whisper.cpp, scrcpy, wl-clipboard, Rust (to build clipboard-sync) |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) / Qt | GPL-3.0 / LGPL | Arrow Pad, NordVPN tray, installer window (installed with pip, not bundled) |
| [pyopenvr](https://github.com/cmbruns/pyopenvr), OpenVR | BSD-3-Clause | Arrow Pad haptics (with SteamVR's own arm64 `libopenvr_api.so`) |
| [VSCodium](https://github.com/VSCodium/vscodium) | MIT | vscodium tweak (Flathub) |
| [jeepney](https://gitlab.com/takluyver/jeepney) | MIT | wallet-unlock, nordvpn-wg (D-Bus) |
| KDE Wallet / kwallet-pam | LGPL | `wallet-unlock` derives the key the way kwallet-pam does |
| [KDE Breeze icons](https://invent.kde.org/frameworks/breeze-icons) | LGPL-3.0 | glyphs in our menu icons and Arrow Pad toolbar |
| [Noto Color Emoji](https://github.com/googlefonts/noto-emoji) | SIL OFL 1.1 | the 🎤 in the Dictate icon |
| Firefox `resistFingerprinting` (from the Tor Project's Tor Browser) | MPL-2.0 | firefox tweak (settings only) |
| [EFF Cover Your Tracks](https://coveryourtracks.eff.org) | – | how we measured the Firefox tweak |

## Trademarks

Steam, Steam Frame and SteamVR are trademarks of Valve; Signal of Signal Technology
Foundation; NordVPN of Nord Security; Claude of Anthropic; Firefox of Mozilla; Android of
Google. This project isn't affiliated with or endorsed by any of them. NordVPN's public
server API is used to look up servers; Claude Desktop is downloaded from Anthropic's own
repository.
