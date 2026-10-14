---
title: Android Mirror
emoji: 📱
category: Convenience
tier: extras
summary: >-
  Mirror and control an Android phone: aarch64 adb + scrcpy, finds the phone automatically
what: >-
  Mirror and control your Android phone in a desktop window (scrcpy over wireless adb). Finds
  the phone's changing port automatically.
why: >-
  Use your phone without taking the headset off. Google ships `adb` only for x86, so this
  installs an aarch64 build that runs on the Frame.
author: "Genymobile (scrcpy), Android platform tools, Frame Tweaks launcher"
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
  about: The phone mirror's stream and joystick scrolling.
  note: >-
    Picture and frame rate apply the next time the mirror starts (or its gear's Restart stream,
    in VR). Joystick speed applies at once.
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
# Android Mirror: wireless adb + scrcpy

Mirror and control an Android phone in a desktop window.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `adb` (Arch Linux ARM, signature-checked) in `~/.local/lib/android-tools`, Homebrew `scrcpy`, `phone` launcher; in VR, two dashboard patches and a control-only scrcpy server on the phone
> - **🧪 Experimental:** Only the VR extras: aimed laser clicks, joystick scrolling and turning with the phone rely on SteamVR's internal dashboard code and scrcpy's control protocol. After an update of either they switch themselves off, and the mirror works as a plain window.
> - **Unusual access:** Network connection to your phone's wireless debugging; pairing keys in `~/.android` (plain files: anyone with your user can use them to reach the phone while it has wireless debugging on). adb's server listens on a socket only you can use (not TCP port 5037)
> - **Undo:** `./install.sh uninstall adb-scrcpy`
<!-- /generated:glance -->

```sh
./install.sh install adb-scrcpy
```

- **adb for aarch64**: Google only ships x86 platform-tools, so the installer takes
  `adb` from Arch Linux ARM plus the few libraries SteamOS lacks or has too old
  (protobuf, fmt, abseil, libusb). They're kept private in `~/.local/lib/android-tools`.
- **scrcpy** from Homebrew.
- **`phone`** / *Android Mirror* launcher: wireless debugging picks a new port every time
  it's switched on, so `phone` looks it up via mDNS, connects and starts scrcpy.
  Extra args go to scrcpy, e.g. `phone --turn-screen-off`.
- **Which phone:** with one phone advertising, it's taken and remembered (`PHONE_NAME` in
  `~/.config/frame-tweaks/phone.conf`); with several, a list asks which. When the remembered phone isn't in
  sight, you can wait for it (up to 3 minutes, while you turn on Wireless debugging) or use one
  that is. To choose again: Android Mirror's **Choose phone…** (right-click its menu entry) or
  `phone --pick`.
  The stream is 1024 pixels on its long side at up to 2 Mbit/s and 60 frames a second, enough for
  VR and light on the wireless link (a heavier stream falls behind the phone); change it there
  with `PHONE_MAX_SIZE=`, `PHONE_BIT_RATE=` and `PHONE_MAX_FPS=`, or with the gear in VR.

## In VR: shaped like the phone
The Steam session makes every app window 1920×1080, so a phone held upright used to show with
wide black bars. `phone-fit` (started by `phone`) gives the mirror window the phone screen's
shape (485×1080 upright, 1920×862 sideways, for a 20:9 phone: it has to fit inside the 1920×1080
screen, or it's shown as 1920×1080 with black bars anyway) and follows it when you rotate
the phone: scrcpy reports the screen's shape to the window system, and a window with a fixed
size keeps it, so its VR panel takes that shape. In desktop mode it does nothing; KWin sizes
the window normally there.

SteamVR starts every floating window as wide as a standard one whatever its shape (so the upright
phone came up over 2 m tall), and keeps that width when its shape changes (so turning the phone
sideways shrank it to a strip). A small dashboard patch (`patch.js`, installed when the
[VR windows](../vr-dashboard/) helper is) gives a floating window that has been upright a long
side of 0.8 m, through the dashboard's own panel-height override: upright it's 0.8 m tall,
sideways 0.8 m wide, so turning the phone just turns the window. Docked in the dashboard, an
upright window gets a standard window's height.

## In VR: clicks land where you aim
The Steam session maps the laser wrongly on a window narrower than its 1920×1080 screen: it
adds the gap it would leave beside the window if it were centred, so on the upright phone every
click landed at the window's left edge. So a see-through layer over the mirror window (a second
dashboard patch, `phone-touch.js`) takes the laser instead and reports where you press, drag and
let go. `phone-touch` (started by `phone`) sends those to the phone as touches, the way scrcpy
does: it starts a second scrcpy server on the phone with only its control channel (no video;
its copy is kept at `/data/local/tmp/sft-phone-touch.jar`, since scrcpy deletes its own), so
nothing goes through the Steam session's input. The layer is there only while `phone-touch`
runs, and covers only the window titled "Android Mirror", the title `phone` gives it.

While the laser rests on the mirror, the joystick scrolls the phone (up/down or sideways, faster
the further you push). SteamVR doesn't pass the joystick to the layer, so `phone-touch` reads it
the way Arrow Pad reads the grips: from the tilt of the controller model's thumbstick part
(through SteamVR's openvr library, installed into the shared Python venv).

**Settings in VR:** the gear below the mirror's lower-left corner opens its settings beside it:
picture size (720 to 1920 pixels on the long side), bit rate (1 to 8 Mbit/s), frame rate (30, 60,
or one of the Steam Frame's refresh rates, 72 to 144) and joystick scrolling speed. They're saved in
`~/.config/frame-tweaks/phone.conf` (only those lines; the rest of the file is kept). *Restart stream* starts
scrcpy again with the new picture settings, without closing the mirror; *Reset to defaults*
removes those lines again. The
[scroll strips](../scroll-strips/) beside the mirror scroll the phone through `phone-touch` too.

## One-time pairing
On the phone: *Developer options → Wireless debugging → Pair device with pairing code*,
then promptly run `adb pair <ip>:<pairing-port> <code>`. The code dies when the
dialog closes.

## Always-on VPN (e.g. Proton on GrapheneOS)
The phone may display its VPN address (like `10.2.0.2`), which you can't reach. It still
advertises its real LAN address over mDNS, and that's what `phone` uses. Check with
`avahi-browse -rt _adb-tls-connect._tcp`. If the phone isn't visible at all, enable
the VPN's "allow LAN connections" option.

## Credits
[scrcpy](https://github.com/Genymobile/scrcpy) (Apache-2.0); `adb` from Android's platform tools (Apache-2.0) as packaged by [Arch Linux ARM](https://archlinuxarm.org). See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status adb-scrcpy` · Remove: `./install.sh uninstall adb-scrcpy`
