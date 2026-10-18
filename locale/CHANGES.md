# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-10-17
- New in `lib/common.sh:186`
  - now: "%s is built for '%s', not aarch64; not installing it"
- New in `lib/common.sh:193`
  - now: "%s %s is older than the %s this release was tested with; not installing it"
- New in `lib/common.sh:386`
  - now: "Couldn't reach PyPI to install %s: check the Internet connection, then try again."
- New in `lib/common.sh:387`
  - now: "%s, the tested version, is no longer on PyPI, so %s isn't installed: a deleted release isn't replaced by another one. Please report this."
- New in `lib/common.sh:389`
  - now: "Couldn't install %s (see above)."
- New in `lib/common.sh:391`
  - now: "PyPI has no build of %s for this Python (%s) and system; installing the newest %s that has one instead. The other tested versions stay."
- New in `packs/core/ydotool/install.sh:14`
  - now: "ydotool didn't start"
- Changed in `packs/core/ydotool/install.sh:18`
  - was: "Arch Linux ARM's current ydotool doesn't run on this SteamOS; keeping the one you have. Missing: %s"
  - now: "Arch Linux ARM's current ydotool doesn't run on this SteamOS (%s); keeping the one you have."
- Changed in `packs/core/ydotool/install.sh:20`
  - was: "Arch Linux ARM's current ydotool doesn't run on this SteamOS. Missing: %s"
  - now: "Arch Linux ARM's current ydotool doesn't run on this SteamOS (%s)."
