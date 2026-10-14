# Icons

App-menu icons, PNG (256×256; Frame Tweaks' own also at 64 and 128), installed into
`~/.local/share/icons/hicolor` because Steam's "+" menu only looks up icons in the hicolor theme.
This folder holds Frame Tweaks' own (`frame-tweaks*.png`); each tweak's icon is in its folder
under `packs/` (installed with `install_icon`, listed as `icon:` in its README's front matter).
[`dev/draw-icons.py`](../dev/draw-icons.py) draws all of the ones below, and is their source.

**From KDE's Breeze icon theme** (Copyright (C) 2014 Uri Herrera and others, LGPL-3.0-or-later;
taken from SteamOS's breeze-icons 6.14.0, `breeze-dark`): a Breeze glyph, white, on a rounded
coloured tile.

| Icon | Breeze glyph | Tile |
|---|---|---|
| `icons/frame-tweaks.png` (and `-64`, `-128`) | `actions/24/configure.svg` | `#7b4fc9` |
| `packs/original/adb-scrcpy/frame-tweaks-phone.png` | `devices/24/smartphone.svg` | `#2e9d4f` |
| `packs/original/arrowpad/frame-tweaks-arrowpad.png` | `devices/24/input-keyboard.svg` | `#3d7bd9` |
| `packs/integrations/nordvpn/frame-tweaks-nordvpn.png` | `devices/24/network-vpn.svg` | `#1f3b73` |
| `packs/original/wallet/frame-tweaks-lock.png` | `actions/22/object-locked.svg` | `#b8860b` |
| `packs/original/snip/frame-tweaks-snip.png` | `apps/48/accessories-screenshot-tool.svg`, as it is | – |

Breeze's licence says that for its icons, the source is their SVG: these icons' source is those
SVGs and `dev/draw-icons.py`, which makes them from them.

**From Noto Color Emoji** (SIL Open Font License 1.1; SteamOS's noto-fonts-emoji 2.042):
`packs/original/dictation/frame-tweaks-dictate.png`, the font's 🎤 drawn on a `#c0392b` tile,
like Arrow Pad's 🎤 button while it records.

The texts of these licences are in [LICENSES/](../LICENSES/): `LGPL-3.0-or-later.txt` (with
`GPL-3.0-or-later.txt`, which it builds on) for the Breeze-based icons, `OFL-1.1.txt` for the
emoji. Everything else in Frame Tweaks is under its MIT [LICENSE](../LICENSE).
