# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-10-17
- New in `get.sh:70`
  - now: "Release channel: %s"
- New in `get.sh:71`
  - now: "FRAME_TWEAKS_CHANNEL: stable or beta"
- New in `get.sh:80`
  - now: "Updating %s (./install.sh update)"
- New in `get.sh:86`
  - now: "Some tweaks didn't update (see above); the window shows which."
- New in `get.sh:98`
  - now: "Couldn't find a release of %s"
- New in `get.sh:99`
  - now: "Installing %s into %s"
- Changed in `gui/prefs_page.py:66`
  - was: "For this window, Arrow Pad, Screen snip, the menu entries and the VR panels. Following the keyboard: Steam's VR keyboard in VR, KDE's layout in desktop mode; a QWERTY or English layout keeps the system's language."
  - now: "For this window, Arrow Pad, Screen snip, the menu entries and the VR panels. Following the keyboard: Steam's VR keyboard in VR, KDE's layout in desktop mode; a QWERTY or English layout keeps the language Steam is set to (or the system's)."
