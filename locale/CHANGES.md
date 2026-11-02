# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-02
- New in `gui/frame-tweaks-gui.py:290`
  - now: "✔ Works on my Frame"
- New in `gui/frame-tweaks-gui.py:291`
  - now: "Report which tweaks work on your SteamOS and SteamVR versions (on GitHub, when you choose to)"
- New in `gui/works_page.py:117`
  - now: "Open the form on GitHub"
- New in `gui/works_page.py:95`
  - now: "Works on my Frame"
- New in `gui/works_page.py:99`
  - now: "Tell others which tweaks work on your SteamOS and SteamVR versions. Below is everything the report says: the versions, and each tweak as a mark only (✔ works, ! needs attention, ⟳ waits for a SteamVR restart, · not installed), not its status text.<br><b>Open the form on GitHub</b> opens it in your browser with this filled in. Nothing is sent unless you submit it there (you sign in on GitHub, and the report is public). Frame Tweaks sends nothing by itself and doesn't remember this."
- New in `packs/core/dictation/dictate:281`
  - now: "Dictation is busy"
- New in `packs/third-party/cuff/README.md`
  - now: "A wrist panel in VR with the time, batteries, quick actions and tabs"
- New in `packs/third-party/cuff/README.md`
  - now: "Cuff"
- New in `packs/third-party/cuff/README.md`
  - now: "Look at the back of your wrist in VR and a panel is there: the time, the headset's, the controllers' and Bluetooth headphones' batteries, six quick actions (dictation, mic mute, passthrough, recenter, the SteamVR keyboard, a screenshot), and tabs for what's playing, audio, a timer and performance. Touch it with the sphere in front of your other controller."
- New in `packs/third-party/cuff/README.md`
  - now: "The Frame has no glanceable status in VR: the time and batteries are behind the dashboard. Linked: [Cuff](https://github.com/Brobert-in-aus/cuff) installs itself on the Frame, the way its README describes, at the commit Frame Tweaks tried it at."
