# steam-frame-tweaks

Productivity tweaks for **desktop mode on the Valve Steam Frame** (SteamOS, aarch64).
Everything installs into your home directory (`~/.local`, user services, Flatpak user
overrides). Nothing touches SteamOS's read-only system partition, so OS updates won't
undo it.

```sh
git clone <this repo> ~/steam-frame-tweaks
cd ~/steam-frame-tweaks
./install.sh                     # list components
./install.sh dictation arrowpad  # install some
./install.sh all
```

Prerequisites: [Homebrew](https://brew.sh) (works on SteamOS aarch64) for `dictation`
and `adb-scrcpy`.

## Tweaks

| Tweak | What you get |
|---|---|
| [**Dictation**](dictation/) | Local Whisper speech-to-text on the Frame's GPU. One shortcut to record, then the text is typed, copied to the clipboard and logged. |
| [**Arrow Pad**](arrowpad/) | Floating nav pad (arrows, Home/End, PgUp/PgDn, one-shot Ctrl/Alt/Shift, F-keys, Copy/Paste, 🎤 dictation) that never steals focus. Includes a guide to which keyboard to use when. |
| [**Full Keyboard**](full-keyboard/) | Installs TaiKeid's full-size VR keyboard (checksum-verified). |
| [**Mouse cursor fix**](cursor/) | Makes the mouse pointer visible in desktop mode. |
| [**Phone Mirror**](adb-scrcpy/) | `adb` for aarch64 + `scrcpy`, plus a launcher that finds your phone's wireless-debugging port automatically. |
| [**Wallet**](wallet/) | One KDE wallet shared by desktop mode and VR (steam-frame-nix's launcher approach), plus KWalletManager. |
| [**Signal**](signal/) | Makes the Flathub Signal store its database key in the shared KDE wallet instead of plaintext. |
| [**Claude Desktop**](claude-desktop/) | Official Linux arm64 beta, installed and updated without apt. |
| [**Tools**](tools/) | `restart-plasmashell`: get the taskbar/system tray back after a crash. |
| [ydotool](ydotool/) | Shared helper for keystroke injection (installed automatically). |

Each folder's README covers usage, configuration and how it works.

## General Frame desktop-mode notes
- **Desktop mode is nested.** Plasma runs inside its own D-Bus session with
  `XDG_RUNTIME_DIR=/run/user/$UID/nested_plasma`. Things launched from shortcuts can
  see a different environment. Several tweaks here work around that.
- **Two sessions, two D-Bus buses**: apps started from the desktop and from VR can get
  different wallets, portals and clipboards. See [wallet](wallet/).
- **Steam on-screen keyboard**: hold **Shift** for ←/→ cursor keys.
- **X11-only on-screen keyboards** (e.g. CoreKeyboard from Flathub) don't appear or
  work under the Wayland desktop.
- **Vulkan apps** may crash in the Gamescope WSI layer; try `DISABLE_GAMESCOPE_WSI=1`.

## Related projects
Other people publishing Frame tweaks (as of October 2026):
- [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix): Home Manager modules
  covering a lot of the same ground (two-session quirks, clipboard, KDE wallet, VR keyboard).
- [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils):
  Tailscale, distrobox from desktop mode, waypipe, mouse cursor, Full Keyboard app.
- [TaiKeid/steam-frame-full-keyboard](https://github.com/TaiKeid/steam-frame-full-keyboard):
  full-size VR keyboard (installed by our `full-keyboard`).
- Dictation alternatives: [techieyann/frame-voice](https://github.com/techieyann/frame-voice)
  (controller-triggered), [groffta/whisper-frame](https://github.com/groffta/whisper-frame)
  (push-to-talk on the Select button), [gripspeak](https://github.com/gripspeak/gripspeak).

## Uninstall

```sh
systemctl --user disable --now ydotoold
wallet-launcher --remove $(wallet-launcher --list)
rm -f ~/.local/bin/{dictate,arrowpad,phone,adb,ydotool,ydotoold,claude-desktop,claude-desktop-update,restart-plasmashell,wallet-launcher,frame-outer-bus}
rm -f ~/.config/environment.d/90-kwin-software-cursor.conf
rm -rf ~/.local/share/{whisper,arrowpad} ~/.local/lib/android-tools ~/.local/opt/claude-desktop
rm -f ~/.local/share/applications/{dictate,arrowpad,phone-mirror,com.anthropic.Claude}.desktop
rm -f ~/.config/systemd/user/ydotoold.service
```
Full Keyboard has its own uninstaller (see its README).
**Leave the Signal override in place.** Once the key lives in the wallet, switching
Signal back to the plaintext store would leave it unable to open its own database.
