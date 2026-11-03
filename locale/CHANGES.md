# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-02
- New in `gui/frame-tweaks-gui.py:750`
  - now: "{version} available (tested by Frame Tweaks)"
- New in `gui/frame-tweaks-gui.py:753`
  - now: "{version} available (not yet tested by Frame Tweaks)"
- New in `gui/frame-tweaks-gui.py:755`
  - now: "A newer release than the one Frame Tweaks tested on a Frame: it may work differently, or not yet on the Frame, and this tweak's page may not match it. Once it's installed, its row offers to go back to the tested version."
- New in `gui/frame-tweaks-gui.py:760`
  - now: "Back to the tested version {version}"
- New in `gui/frame-tweaks-gui.py:761`
  - now: "Installs the version Frame Tweaks tested again, with the project's own installer (its settings stay)."
- New in `install.sh:768`
  - now: "Linked, at the version Frame Tweaks tested, which this release moves to a newer one: %s"
- New in `install.sh:801`
  - now: "link-version ID [tested|newest]"
- New in `install.sh:803`
  - now: "%s isn't linked: it installs what Frame Tweaks has"
- New in `install.sh:809`
  - now: "No tested version: it installs its newest."
- New in `install.sh:812`
  - now: "The version Frame Tweaks tested: %s"
- New in `install.sh:813`
  - now: "Installed: %s"
- New in `install.sh:814`
  - now: "Its newest: %s"
- New in `install.sh:815`
  - now: "Its newest: couldn't look it up"
- New in `install.sh:816`
  - now: "To install one: %s"
- New in `install.sh:821`
  - now: "%s has no tested version: it installs its newest (./install.sh install %s)"
- New in `lib/link.sh:51`
  - now: "installed by its own installer: the version Frame Tweaks tested (%s)"
- New in `lib/link.sh:53`
  - now: "installed by its own installer: %s, not the version Frame Tweaks tested (%s)"
- New in `lib/link.sh:55`
  - now: "installed by its own installer: its newest version, not yet tested by Frame Tweaks"
- New in `lib/link.sh:71`
  - now: "%s has no tested version here: it installs its newest"
- New in `lib/link.sh:74`
  - now: "Installing the newest %s, not yet tested by Frame Tweaks, with its own installer (from the project):"
- New in `lib/link.sh:77`
  - now: "Installing %s %s, the version Frame Tweaks tested, with its own installer (from the project):"
- Changed in `packs/third-party/full-keyboard/README.md`
  - was: "Steam's own VR keyboard lacks keys the desktop needs, such as up/down arrows, Ctrl and F-keys. Linked: it installs from its newest release with its own installer, the way its README describes."
  - now: "Steam's own VR keyboard lacks keys the desktop needs, such as up/down arrows, Ctrl and F-keys. Linked: it installs the release Frame Tweaks tested with its own installer, the way its README describes."
- Changed in `packs/third-party/full-keyboard/README.md`
  - was: "TaiKeid's full-size VR keyboard, shown with the SteamVR dashboard, installed from its newest release"
  - now: "TaiKeid's full-size VR keyboard, shown with the SteamVR dashboard, installed from the release Frame Tweaks tested"
- Changed in `packs/third-party/knockthru/README.md`
  - was: "Checking the room means finding the Room View button in the dashboard, or a controller binding. A knock works with a controller in your hand or set down. Linked: it installs from its newest release with its own installer, the way its README describes."
  - now: "Checking the room means finding the Room View button in the dashboard, or a controller binding. A knock works with a controller in your hand or set down. Linked: it installs the release Frame Tweaks tested with its own installer, the way its README describes."
- Changed in `packs/third-party/perf-overlay/README.md`
  - was: "The Frame doesn't show its own temperatures, clocks or memory while you play, so a slowdown or a hot headset is hard to explain. Linked: it installs from its newest release with its own installer, the way its README describes."
  - now: "The Frame doesn't show its own temperatures, clocks or memory while you play, so a slowdown or a hot headset is hard to explain. Linked: it installs the release Frame Tweaks tested with its own installer, the way its README describes."
