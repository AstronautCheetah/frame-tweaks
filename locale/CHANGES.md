# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-03
- New in `lib/vrbindings.py:109`
  - now: "SteamVR refused {what} (HTTP {code})"
- New in `lib/vrbindings.py:111`
  - now: "SteamVR isn't running (nothing answers on {url}); nothing was changed."
- New in `lib/vrbindings.py:114`
  - now: "SteamVR's answer to {what} isn't JSON"
- New in `lib/vrbindings.py:120`
  - now: "SteamVR has no binding of {app} for {controller}"
- New in `lib/vrbindings.py:129`
  - now: "SteamVR couldn't load the binding {url}"
- New in `lib/vrbindings.py:136`
  - now: "SteamVR didn't select the binding {url}"
- New in `lib/vrbindings.py:144`
  - now: "the edit file must be a JSON object"
- New in `lib/vrbindings.py:147`
  - now: "unknown key in the edit file: {keys}"
- New in `lib/vrbindings.py:151`
  - now: "\"{key}\" must be a name such as {example}"
- New in `lib/vrbindings.py:155`
  - now: "\"edits\" must be a list of at least one edit"
- New in `lib/vrbindings.py:159`
  - now: "edit {n}: \"op\" must be one of: {ops}"
- New in `lib/vrbindings.py:162`
  - now: "edit {n}: unknown key: {keys}"
- New in `lib/vrbindings.py:165`
  - now: "edit {n}: \"{key}\" must be a text"
- New in `lib/vrbindings.py:170`
  - now: "edit {n}: \"action_set\" starts /actions/, \"path\" /user/"
- New in `lib/vrbindings.py:179`
  - now: "can't read {file}: {why}"
- New in `lib/vrbindings.py:181`
  - now: "{file} isn't JSON: {why}"
- New in `lib/vrbindings.py:219`
  - now: "{path} has no source in {set}: say its \"mode\" (button, joystick...) to add one"
- New in `lib/vrbindings.py:353`
  - now: "a patch's name is lowercase letters, digits, '.', '_' and '-' (e.g. the tweak's id)"
- New in `lib/vrbindings.py:361`
  - now: "A patch named {name} already changes another binding ({key}); restore it first."
- New in `lib/vrbindings.py:366`
  - now: "The binding changed since Frame Tweaks patched it (for: {names}). Restore those patches first: that keeps the binding chosen since."
- New in `lib/vrbindings.py:371`
  - now: "SteamVR uses a copy Frame Tweaks has no record of ({url}): choose another binding in SteamVR's controller settings first."
- New in `lib/vrbindings.py:376`
  - now: "{name}: already active"
- New in `lib/vrbindings.py:382`
  - now: "{name}: the binding already reads that way; nothing to change"
- New in `lib/vrbindings.py:397`
  - now: "{name}: patched (SteamVR may need a restart before it acts on it)"
- New in `lib/vrbindings.py:408`
  - now: "{name}: no such patch; nothing to restore"
- New in `lib/vrbindings.py:413`
  - now: "{name}: the binding was changed since Frame Tweaks patched it; left as it is"
- New in `lib/vrbindings.py:439`
  - now: "{name}: restored (SteamVR may need a restart before it acts on it)"
- New in `lib/vrbindings.py:472`
  - now: "show [--controller C] [--app KEY] [--json]"
- New in `lib/vrbindings.py:482`
  - now: "patch NAME EDIT-FILE"
- New in `lib/vrbindings.py:486`
  - now: "restore NAME"
- New in `lib/vrbindings.py:491`
  - now: "No SteamVR binding patches."
- New in `lib/vrbindings.py:493`
  - now: "active"
- New in `lib/vrbindings.py:493`
  - now: "not active (the binding was changed since)"
- New in `lib/vrbindings.py:494`
  - now: "SteamVR not running"
- New in `lib/vrbindings.py:497`
  - now: "unknown command: {cmd}"

## 2026-11-04
- New in `packs/core/tools/recover-session:106`
  - now: "Put back the VR session's display (%s), which Steam needs to start."
