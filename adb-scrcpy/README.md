# Android Mirror: wireless adb + scrcpy

Mirror and control an Android phone in a desktop window.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `adb` (Arch Linux ARM, signature-checked) in `~/.local/lib/android-tools`, Homebrew `scrcpy`, `phone` launcher; in VR, two dashboard patches and a control-only scrcpy server on the phone
> - **Unusual access:** Network connection to your phone's wireless debugging; pairing keys in `~/.android`
> - **Undo:** `./install.sh uninstall adb-scrcpy`
<!-- /generated:glance -->

```sh
./install.sh adb-scrcpy
```

- **adb for aarch64**: Google only ships x86 platform-tools, so the installer takes
  `adb` from Arch Linux ARM plus the few libraries SteamOS lacks or has too old
  (protobuf, fmt, abseil, libusb). They're kept private in `~/.local/lib/android-tools`.
- **scrcpy** from Homebrew.
- **`phone`** / *Android Mirror* launcher: wireless debugging picks a new port every time
  it's switched on, so `phone` looks it up via mDNS, connects and starts scrcpy.
  Extra args go to scrcpy, e.g. `phone --turn-screen-off`.
  With several phones around, set `PHONE_NAME="Pixel 9"` in `~/.config/phone.conf`.

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
sideways 0.8 m wide, so turning the phone just turns the window.

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
[scrcpy](https://github.com/Genymobile/scrcpy) (Apache-2.0); `adb` from Android's platform tools (Apache-2.0) as packaged by [Arch Linux ARM](https://archlinuxarm.org). See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status adb-scrcpy` · Remove: `./install.sh uninstall adb-scrcpy`
