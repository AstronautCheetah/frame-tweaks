# Android Mirror: wireless adb + scrcpy

Mirror and control an Android phone in a desktop window.

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
