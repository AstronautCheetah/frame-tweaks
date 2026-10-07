# steam-frame-tweaks

Productivity tweaks for **desktop mode on the Valve Steam Frame** (SteamOS, aarch64).
Everything installs into your home directory (`~/.local`). Nothing touches
SteamOS's read-only system partition, so OS updates won't undo it, and
removing a component is just deleting its files.

```sh
git clone <this repo> ~/steam-frame-tweaks
cd ~/steam-frame-tweaks
./install.sh                 # list components
./install.sh dictation arrowpad
```

Prerequisites: [Homebrew](https://brew.sh) (works on SteamOS aarch64) for
`dictation` and `adb-scrcpy`. Your user must be in the `input` group
(the default on SteamOS) for `ydotool`.

## Components

| Component | What you get |
|---|---|
| `dictation` | **Local speech-to-text** with whisper.cpp on the Frame's GPU (~3.5 s for 11 s of speech with `small.en`). Run `dictate` (or bind *Dictate (toggle)* to a shortcut): first press starts recording (chime), second press transcribes. The text is typed into the focused window, copied to the clipboard (shows in Klipper), and appended to `~/.local/share/dictation-history.txt`. |
| `arrowpad` | **Arrow Pad**: a floating, always-on-top pad with ↑↓←→, Home/End, PgUp/PgDn, Esc, Tab, Backspace, Del, Enter, and sticky Shift/Ctrl. Tapping it **never steals focus**, so keys go to the app you're working in. Holding a key repeats. This fills the gap in the Steam on-screen keyboard, which has no arrow keys. |
| `adb-scrcpy` | `adb` for aarch64 (Google ships x86 only) + `scrcpy`, plus a **Phone Mirror** launcher (`phone`) that finds your phone's ever-changing wireless-debugging port via mDNS and mirrors it. |
| `claude-desktop` | The official **Claude Desktop** Linux beta (arm64 `.deb`, SHA256-verified, unpacked without apt). `claude-desktop-update` updates it. |
| `tools` | `restart-plasmashell`: brings back the taskbar/system tray if plasmashell crashes. |
| `ydotool` | Keystroke injection via uinput + a user service; installed automatically by `dictation` and `arrowpad`. |

## Configuration

- **Dictation**: `~/.config/dictate.conf` (see `dictation/dictate.conf.example`):
  vocabulary hints (`DICTATE_PROMPT`), model choice, copy-only mode.
  Troubleshooting log: `/run/user/$UID/dictate/dictate.log`.
- **Arrow Pad**: `arrowpad --scale 1.5` for bigger buttons (or `ARROWPAD_SCALE`).
- **Phone Mirror**: `~/.config/phone.conf` with `PHONE_NAME="Pixel 9"` if more than
  one phone is on the network. Extra args go to scrcpy: `phone --turn-screen-off`.

## Notes and gotchas found along the way

- **Desktop mode runs nested.** Plasma runs in its own D-Bus session with
  `XDG_RUNTIME_DIR=/run/user/$UID/nested_plasma`. Apps started from shortcuts
  or the launcher may instead see `/run/user/$UID`, where there's no Wayland
  socket, so `wl-copy` fails silently. The dictate script handles this.
- **whisper.cpp + Vulkan** crashes inside the Gamescope WSI layer; set
  `DISABLE_GAMESCOPE_WSI=1` (the dictate script does).
- **Steam on-screen keyboard**: hold **Shift** to get ← / → cursor keys.
  There are no up/down keys, hence Arrow Pad.
- **X11-only on-screen keyboards** (e.g. CoreKeyboard) don't show up or work
  under the Wayland desktop.
- **Wireless ADB with an always-on VPN** (e.g. Proton on GrapheneOS): the phone
  may display its VPN address, but it still advertises its LAN address over
  mDNS, which is what `phone` uses. Pairing codes expire once the pairing dialog
  closes, so pair promptly.
- **Arrow Pad focus trick**: it runs under XWayland with the X11
  "doesn't accept input focus" hint, which KWin honours. Native Wayland has no
  equivalent for normal windows.

## Uninstall

```sh
systemctl --user disable --now ydotoold
rm -f ~/.local/bin/{dictate,arrowpad,phone,adb,ydotool,ydotoold,claude-desktop,claude-desktop-update,restart-plasmashell}
rm -rf ~/.local/share/{whisper,arrowpad} ~/.local/lib/android-tools ~/.local/opt/claude-desktop
rm -f ~/.local/share/applications/{dictate,arrowpad,phone-mirror,com.anthropic.Claude}.desktop
rm -f ~/.config/systemd/user/ydotoold.service
```
