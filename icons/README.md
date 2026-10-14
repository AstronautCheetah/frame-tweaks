# Icons

App-menu icons, PNG (256×256; Frame Tweaks' own also at 64 and 128), installed into `~/.local/share/icons/hicolor` because Steam's
"+" menu only looks up icons in the hicolor theme. This folder holds Frame Tweaks' own
(`frame-tweaks*.png`); each tweak's icon is in its folder under `packs/original/` (installed with
`install_icon`, listed as `icon:` in its README's front matter). Where they come from:

- `frame-tweaks-dictate.png`: the Arrow Pad's 🎤 button in its recording state, using the
  Noto Color Emoji microphone (SIL Open Font License 1.1).
- The others: white glyphs from KDE's Breeze icon theme (LGPL-3.0) on colored tiles:
  `smartphone` (Android Mirror), `input-keyboard` (Arrow Pad), `network-vpn` (NordVPN),
  `configure` (Frame Tweaks), `object-locked` (Lock wallet).
- `frame-tweaks-snip.png`: Breeze's `accessories-screenshot-tool` app icon (LGPL-3.0), as is.

The texts of these licences are in [LICENSES/](../LICENSES/): `LGPL-3.0-only.txt` (with
`GPL-3.0-only.txt`, which it builds on) for the Breeze-based icons, `OFL-1.1.txt` for the emoji.
Everything else in Frame Tweaks is under its MIT [LICENSE](../LICENSE).
