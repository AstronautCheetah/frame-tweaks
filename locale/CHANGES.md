# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-03
- New in `gui/frame-tweaks-gui.py:278`
  - now: "Search the tweaks"
- New in `gui/frame-tweaks-gui.py:283`
  - now: "Search: name, description, category"
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
- New in `install.sh:666`
  - now: "The shared files the tweaks load (translations, tooltips) are up to date again; programs running now use them from their next start."
- New in `packs/core/arrowpad/arrowpad.py:1445`
  - now: "No keyboard holds a key. If Shift, Ctrl, Alt or Super still acts as held, the stuck state is inside SteamVR, and only restarting SteamVR clears it: ⟳ Restart SteamVR in the Frame Tweaks window, or 'steamvr restart' in a terminal."
- Changed in `packs/core/dictation/README.md`
  - was: "Voice activity detection"
  - now: "Whisper voice activity detection"
- New in `packs/core/snip/frame-snip:1930`
  - now: "Kept as {path}"
- New in `packs/core/snip/frame-snip:470`
  - now: "The snip is black: this window can't be captured, so there's no text to read."
- New in `packs/core/snip/frame-snip:471`
  - now: "No text found in the snip."
- New in `packs/third-party/perf-overlay/README.md`
  - now: "Show"
- New in `packs/third-party/perf-overlay/run.sh:12`
  - now: "Not installed: tick Performance Overlay and Apply changes first."
- New in `packs/third-party/perf-overlay/run.sh:16`
  - now: "From now on it starts with SteamVR, as its installer meant to set up."
- New in `packs/third-party/perf-overlay/run.sh:18`
  - now: "It is not set to start with SteamVR, and that could not be fixed: run %s in a terminal."
- New in `packs/third-party/perf-overlay/run.sh:23`
  - now: "SteamVR is not running: the panel shows once it is."
- New in `packs/third-party/perf-overlay/run.sh:27`
  - now: "Started: look for the panel in VR; its Perf tab in the SteamVR dashboard has the settings."
- New in `packs/third-party/perf-overlay/run.sh:35`
  - now: "Could not start %s: see %s"
- New in `packs/third-party/perf-overlay/run.sh:35`
  - now: "Hidden in VR (Show brings it back)."
- New in `packs/third-party/perf-overlay/run.sh:36`
  - now: "Shown in VR."
- New in `packs/third-party/perf-overlay/run.sh:38`
  - now: "A copy started from the menu held the panel without showing it: ended."
- New in `packs/third-party/perf-overlay/status.sh:13`
  - now: "installed, but not set to start with SteamVR (its installer's enable step fails from desktop mode): Show on its row sets it, or %s"
- New in `packs/third-party/perf-overlay/status.sh:19`
  - now: "installed; closed from its dashboard until the next SteamVR start (Show on its row starts it again)"
- New in `packs/third-party/perf-overlay/status.sh:20`
  - now: "a copy started from the menu is running outside its service and shows nothing: Show on its row ends it, so the service can show the panel"
- New in `packs/third-party/perf-overlay/status.sh:21`
  - now: "installed, but its service failed (exit status %s): Show on its row starts it again; its log: %s"
- New in `packs/third-party/perf-overlay/status.sh:24`
  - now: "installed; starts with the next SteamVR start (Show on its row starts it now)"
