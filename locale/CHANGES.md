# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-03
- New in `gui/settings_page.py:66`
  - now: "Not used with the {setting} you chose."
- New in `gui/wallet_page.py:575`
  - now: "Show all Homebrew commands ({n} more formula)"
  - plural: "Show all Homebrew commands ({n} more formulae)"
- New in `gui/wallet_page.py:578`
  - now: "Show all Homebrew commands"
- New in `gui/wallet_page.py:581`
  - now: "Also list the commands of formulae installed for another one, and those Frame Tweaks' tweaks run, to protect any of them"
- New in `gui/wallet_page.py:596`
  - now: "Installed for another formula, not by you."
- New in `gui/wallet_page.py:597`
  - now: "A Frame Tweaks tweak runs it: protected, it can wait for the wallet password where nobody sees the dialog (Dictation in VR, say)."
- New in `gui/wallet_page.py:606`
  - now: "Protect selected"
- Changed in `packs/core/dictation/README.md`
  - was: "Voice activity detection"
  - now: "Whisper voice activity detection"
