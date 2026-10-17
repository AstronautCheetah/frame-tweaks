# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-10-17
- New in `gui/frame-tweaks-gui.py:628`
  - now: "Tick every tweak in this category"
- New in `gui/frame-tweaks-gui.py:629`
  - now: "Untick every tweak in this category (installed ones are removed when you apply the changes)"
- New in `packs/core/arrowpad/vroverlay.py:343`
  - now: "While Steam's keyboard is open, Arrow Pad only slides when you drag it. To move it closer, further away or turn it, use the bar under it."
- New in `packs/core/snip/frame-snip:1414`
  - now: "While Steam's keyboard is open, this panel can only slide. Close the keyboard to move it closer, further away or turn it."
- New in `packs/core/snip/frame-snip:1459`
  - now: "While Steam's keyboard is open, this panel only slides when you drag it. To move it closer, further away or turn it, use the bar under it."
- New in `packs/core/snip/frame-snip:772`
  - now: "Volume down"
- New in `packs/core/snip/frame-snip:773`
  - now: "Volume up"
- Changed in `packs/core/vr-dashboard/README.md`
  - was: "The shared part of the VR environment tweaks (Curved world windows, Back to the previous window, Pick up when floating, Scroll strips): it puts their small patches into SteamVR's dashboard while SteamVR runs. Android Mirror uses it too when it's there. Installed automatically."
  - now: "The shared part of the VR environment tweaks (Curved world windows, Back to the previous window, Pick up when floating, Scroll strips): it puts their small patches into SteamVR's dashboard while SteamVR runs. Android Mirror uses it too when it's there. Installed automatically. Its own patches help Frame Tweaks' panels in VR (Arrow Pad, Screen snip's narration panel) with Steam's keyboard: pressing one leaves the keyboard with the window you're typing in, and while it's open, SteamVR's grab bar under each panel moves it anywhere."
