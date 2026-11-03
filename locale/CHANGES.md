# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-03
- Changed in `packs/core/adb-scrcpy/README.md`
  - was: "Button below the mirror: App switcher"
  - now: "Mirror button: App switcher"
- New in `packs/core/adb-scrcpy/README.md`
  - now: "Mirror button: Back"
- Changed in `packs/core/adb-scrcpy/README.md`
  - was: "Button below the mirror: Notifications (open or close the phone's panel)"
  - now: "Mirror button: Notifications (open or close the phone's panel)"
- Changed in `packs/core/adb-scrcpy/README.md`
  - was: "Button below the mirror: Power (screen off or on)"
  - now: "Mirror button: Power (screen off or on)"
- Changed in `packs/core/adb-scrcpy/README.md`
  - was: "Button below the mirror: Volume down"
  - now: "Mirror button: Volume down"
- Changed in `packs/core/adb-scrcpy/README.md`
  - was: "Button below the mirror: Volume up"
  - now: "Mirror button: Volume up"
- Changed in `packs/core/adb-scrcpy/README.md`
  - was: "Picture, frame rate and the clipboard apply the next time the mirror starts (or its gear's Restart stream, in VR). Joystick speed and the buttons below the mirror apply at once, and so does the time it disconnects after, counted from when you change it."
  - now: "Picture, frame rate and the clipboard apply the next time the mirror starts (or its gear's Restart stream, in VR). Joystick speed and the mirror's buttons apply at once, and so does the time it disconnects after, counted from when you change it."
- New in `packs/core/adb-scrcpy/README.md`
  - now: "The mirror's buttons go"
- New in `packs/core/adb-scrcpy/phone-touch.js:275`
  - now: "Above"
- New in `packs/core/adb-scrcpy/phone-touch.js:275`
  - now: "Below"
- New in `packs/core/adb-scrcpy/phone-touch.js:275`
  - now: "Buttons"
- New in `packs/core/adb-scrcpy/phone-touch.js:441`
  - now: "Drag to change the order"
