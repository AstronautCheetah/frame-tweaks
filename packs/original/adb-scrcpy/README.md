---
title: Android Mirror
emoji: 📱
category: Convenience
tier: extras
summary: >-
  See and control your Android phone in a window, over Wi-Fi, without taking the headset off
what: >-
  Shows your Android phone's screen in a window you can click, type and scroll in, over Wi-Fi
  (scrcpy with Android's wireless debugging). It finds the phone on the network by itself.
why: >-
  Use your phone without taking the headset off. Google's `adb` tool doesn't run on the Frame's
  ARM processor, so this installs a build that does; in VR, the window takes the phone's shape.
author: "Genymobile (scrcpy), Android platform tools, Frame Tweaks launcher"
sudo: homebrew
source: {relation: uses, url: https://github.com/Genymobile/scrcpy}
experimental: >-
  Only the VR extras: aimed laser clicks, joystick scrolling and turning with the phone rely on
  SteamVR's internal dashboard code and scrcpy's control protocol. After an update of either
  they switch themselves off, and the mirror works as a plain window.
icon: {file: frame-tweaks-phone.png}
run: {label: Open}
settings:
  file: ~/.config/frame-tweaks/phone.conf
  format: shell
  about: The phone mirror's stream, joystick scrolling, and its clipboard.
  note: >-
    Picture, frame rate and the clipboard apply the next time the mirror starts (or its gear's
    Restart stream, in VR). Joystick speed applies at once.
  options:
    - key: PHONE_MAX_SIZE
      title: "Picture size (long side, pixels)"
      default: "1024"
      choices:
        - {label: "720", value: "720"}
        - {label: "800", value: "800"}
        - {label: "1024", value: "1024"}
        - {label: "1280", value: "1280"}
        - {label: "1600", value: "1600"}
        - {label: "1920", value: "1920"}
    - key: PHONE_BIT_RATE
      title: Bit rate (Mbit/s)
      default: "2M"
      choices:
        - {label: "1", value: "1M"}
        - {label: "1.5", value: "1500K"}
        - {label: "2", value: "2M"}
        - {label: "3", value: "3M"}
        - {label: "4", value: "4M"}
        - {label: "6", value: "6M"}
        - {label: "8", value: "8M"}
    - key: PHONE_MAX_FPS
      title: "Frame rate (fps, at most; 72-144: the Steam Frame's refresh rates)"
      default: "60"
      choices:
        - {label: "30", value: "30"}
        - {label: "60", value: "60"}
        - {label: "72", value: "72"}
        - {label: "80", value: "80"}
        - {label: "90", value: "90"}
        - {label: "96", value: "96"}
        - {label: "108", value: "108"}
        - {label: "120", value: "120"}
        - {label: "144", value: "144"}
    - key: PHONE_STICK_SPEED
      title: Joystick scrolling
      default: "15"
      choices:
        - {label: Slow, value: "8"}
        - {label: Medium, value: "15"}
        - {label: Fast, value: "25"}
    - key: PHONE_CLIPBOARD
      title: Share the clipboard with the phone
      default: "both"
      checkbox: true
      choices:
        - {label: Shared, value: "both"}
        - {label: Not shared, value: "off"}
  actions:
    - label: "Forget {PHONE_NAME}"
      script: phone
      args: [--forget]
      when: PHONE_NAME
      about: >-
        Android Mirror stops connecting to this phone by default. Next time it takes the phone in
        sight, or asks which if there are several.
wallet_apps: [android-mirror]
changes: >-
  `adb` (Arch Linux ARM, signature-checked) in `~/.local/lib/android-tools`, Homebrew `scrcpy`,
  `phone` launcher; in VR, two dashboard patches and a control-only scrcpy server on the phone
access: >-
  Network connection to your phone's wireless debugging; pairing keys in `~/.android` (plain
  files: anyone with your user can use them to reach the phone while it has wireless debugging
  on). adb's server listens on a socket only you can use (not TCP port 5037)
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall adb-scrcpy`"
---
# Android Mirror

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Shows your Android phone's screen in a window you can click, type and scroll in, over Wi-Fi (scrcpy with Android's wireless debugging). It finds the phone on the network by itself.

**Why on a Steam Frame:** Use your phone without taking the headset off. Google's `adb` tool doesn't run on the Frame's ARM processor, so this installs a build that does; in VR, the window takes the phone's shape.
<!-- /generated:intro -->

## Requirements
- **An Android phone with Android 11 or newer** (Wireless debugging arrived in Android 11), on
  **the same Wi-Fi** as the Frame. Use the phone's main (owner) profile: Wireless debugging
  isn't available in other profiles.
- **Developer options turned on:** *Settings → About phone*, tap *Build number* seven times
  (the menu names vary a little between phone makers).
- **Wireless debugging turned on:** *Settings → System → Developer options → Wireless
  debugging*. The phone asks whether to allow it on this network.

> **Before you turn these on, consider what they allow.** Wireless debugging lets a paired
> computer control the phone fully: see the screen, tap and type, install and remove apps, and
> read files. The Frame keeps its pairing key in your home folder (`~/.android/`), so anyone who
> gets into your Frame account could do the same while the phone's Wireless debugging is on.
> Turn it off when you're not mirroring (pairing is remembered, so turning it back on is
> enough), and don't leave it on on public or shared Wi-Fi. Some apps, such as banking or
> payment apps and phones managed by an employer, refuse to run or warn while Developer
> options are on.

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install adb-scrcpy
```

It installs [Homebrew](../homebrew/) first if you don't have it (that needs your sudo password
once).

**Then pair your phone, once:**

1. On the phone, turn on Developer options, then open *Developer options → Wireless debugging →
   Pair device with pairing code*. The phone must be on the same Wi-Fi as the Frame.
2. On the Frame, in a terminal, run this straight away with the address, port and code the
   phone shows (the code stops working when that dialog closes):

   ```sh
   adb pair <ip>:<pairing-port> <code>
   ```

Later, if Android Mirror can't connect because the phone forgot the Frame (or it's a new phone),
it offers **Pair it again**: open *Pair device with pairing code* on the phone, and enter the
six-digit code when asked. No terminal needed. Or **Forget** the phone, so Android Mirror stops
choosing it by default.

## Use
1. On the phone, turn on *Wireless debugging*.
2. Open **Android Mirror** from the app menu (or press **Open** on its row in Frame Tweaks, or
   run `phone` in a terminal).

The phone's screen opens in a window; click and type in it as on the phone. Close the window
to stop.

**Which phone:** if only one phone is advertising wireless debugging, Android Mirror uses it and
remembers it. If there are several, it asks which. If the remembered phone isn't there, it
offers to wait for it (up to 3 minutes, while you turn on Wireless debugging) or to use one
that is. To choose again, right-click Android Mirror in the app menu and pick **Choose phone…**,
or run `phone --pick`.

Anything you add after `phone` goes to scrcpy, for example `phone --turn-screen-off` to keep
the phone's own screen dark while you mirror it.

### In VR
Opened from VR, the mirror gets a few extras (they need the
[VR dashboard patching helper](../vr-dashboard/), which the VR environment tweaks install):

- **Shaped like the phone:** the window is upright when the phone is upright and sideways when
  it's sideways, and keeps a sensible size when you turn the phone.
- **Clicks land where you aim** with the laser, and you can drag.
- **Joystick scrolling:** while the laser rests on the mirror, push the joystick to scroll the
  phone (further means faster). The [scroll strips](../scroll-strips/) beside the window scroll
  it too.
- **A gear** below the window's lower-left corner opens its settings beside it (see
  [Settings](#settings)). *Restart stream* applies picture changes without closing the mirror;
  *Reset to defaults* puts them back.

## Settings
Change these with the **⚙ Settings** button on its row in Frame Tweaks, with the gear in VR, or in
`~/.config/frame-tweaks/phone.conf`:

| Setting | Default | Choices |
|---|---|---|
| Picture size (long side, `PHONE_MAX_SIZE`) | 1024 pixels | 720 to 1920 |
| Bit rate (`PHONE_BIT_RATE`) | 2 Mbit/s | 1 to 8 |
| Frame rate (at most, `PHONE_MAX_FPS`) | 60 | 30, 60, or one of the Frame's refresh rates, 72 to 144 |
| Joystick scrolling (`PHONE_STICK_SPEED`) | Medium | Slow, Medium, Fast |
| Share the clipboard with the phone (`PHONE_CLIPBOARD`) | Shared (`both`) | Shared, Not shared (`off`) |

The defaults are enough for VR and keep the Wi-Fi link light; a heavier stream can fall
behind the phone. Picture size, bit rate, frame rate and the clipboard apply the next time the
mirror starts (or after *Restart stream* in VR); joystick speed applies at once. The chosen
phone is saved in the same file (`PHONE_NAME`).

**The clipboard with the phone.** Shared (scrcpy's way): what you paste in the mirror (Ctrl+V)
is first copied to the phone, and whatever the phone copies comes to the Frame's clipboard, and
from there to the desktop and VR with [Shared clipboard](../../integrations/clipboard/). So a
password copied on the phone reaches the Frame, and one you paste into the mirror stays in the
phone's clipboard (and its keyboard's clipboard history, if it keeps one). Not shared: each keeps
its own; Ctrl+V in the mirror pastes the phone's clipboard.

## How it works
- **adb for the Frame:** Google only ships `adb` (Android's debugging tool) for x86 PCs. The
  installer takes the ARM build from Arch Linux ARM, signature-checked, plus the few libraries
  SteamOS lacks or has too old (protobuf, fmt, abseil, libusb). They're kept private in
  `~/.local/lib/android-tools`, so nothing else on the system uses them.
- **adb's server is private:** it listens on a socket file only your user can open, instead of
  the usual network port 5037 that any program on the Frame could use to reach a connected
  phone.
- **scrcpy** (the program that shows and controls the phone) comes from Homebrew.
- **Finding the phone:** wireless debugging picks a new port each time it's turned on. `phone`
  looks the phone up on the local network (mDNS), connects, and starts scrcpy.
- **Reconnecting:** `phone` checks every 5 seconds that the phone still answers. If the
  connection drops, it closes the frozen picture and reconnects (for up to a minute).
- **In VR**, `phone-fit` gives the window the phone screen's shape. The Steam session makes
  every app window 1920×1080, so an upright phone would otherwise sit between wide black bars.
  A dashboard patch (`patch.js`) keeps the window's long side at 0.8 m, so turning the phone
  turns the window instead of shrinking it.
- **Clicks in VR:** the Steam session puts laser clicks on so narrow a window at its left edge.
  So a second dashboard patch (`phone-touch.js`) puts a see-through layer over the window
  titled "Android Mirror". `phone-touch` sends what you do on it to the phone as touches,
  through a second, control-only scrcpy server on the phone (kept at
  `/data/local/tmp/sft-phone-touch.jar`). It reads the joystick from SteamVR (its openvr
  library, installed into Frame Tweaks' shared Python environment).

## Good to know
- **An always-on VPN on the phone:** the phone may show its VPN address, which the Frame can't
  reach. It still announces its real local address on the network, and that's what `phone`
  uses. If the phone isn't found at all, turn on the VPN's option to allow local network (LAN)
  connections. To see what the phone announces: `avahi-browse -rt _adb-tls-connect._tcp`.
- **The VR extras switch themselves off** after a scrcpy or SteamVR update they weren't tested
  with; the mirror then works as a plain 16:9 window. For a new scrcpy version, the status line
  says so.
- If you install a VR environment tweak after this one, reinstall Android Mirror to add its VR
  extras.
- **Removing the tweak** keeps your pairing keys (`~/.android`), scrcpy (`brew uninstall
  scrcpy` removes it) and your settings.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `adb` (Arch Linux ARM, signature-checked) in `~/.local/lib/android-tools`, Homebrew `scrcpy`, `phone` launcher; in VR, two dashboard patches and a control-only scrcpy server on the phone
- **🧪 Experimental:** Only the VR extras: aimed laser clicks, joystick scrolling and turning with the phone rely on SteamVR's internal dashboard code and scrcpy's control protocol. After an update of either they switch themselves off, and the mirror works as a plain window.
- **Unusual access:** Network connection to your phone's wireless debugging; pairing keys in `~/.android` (plain files: anyone with your user can use them to reach the phone while it has wireless debugging on). adb's server listens on a socket only you can use (not TCP port 5037)
- **Undo:** `./install.sh uninstall adb-scrcpy`
<!-- /generated:changes -->

## Credits
[scrcpy](https://github.com/Genymobile/scrcpy) by Genymobile (Apache-2.0); `adb` from Android's
platform tools (Apache-2.0), as packaged by [Arch Linux ARM](https://archlinuxarm.org). Its menu icon is a [KDE Breeze](https://invent.kde.org/frameworks/breeze-icons) glyph
(LGPL-3.0-or-later) on a coloured tile, drawn by `dev/draw-icons.py`
([icons/README.md](../../../icons/README.md)).
See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status adb-scrcpy` · Remove: `./install.sh uninstall adb-scrcpy`
