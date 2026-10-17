# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-10-17
- New in `packs/core/arrowpad/arrowpad.py:1545`
  - now: "Hold ✕ to close Arrow Pad"
- New in `packs/core/arrowpad/arrowpad.py:383`
  - now: "Close (hold it)"
- Changed in `packs/core/charge-limit/README.md`
  - was: "Charging stops at this level and starts again 1% below it. Plugged in at the limit, the Frame runs mostly from the charger or power bank. A lower limit wears the battery a little less."
  - now: "Charging stops at this level and starts again 1% below it. Plugged in at the limit, the Frame runs mostly from the charger or power bank. A lower limit wears the battery a little less. The level is the battery's own reading, as KDE shows it; Steam's dashboard shows a higher figure for the same charge (about 8 points more around 80%: 78% here is 86% there)."
- Changed in `packs/core/charge-limit/status.sh:23`
  - was: "Limit off: charges to 100%% (now %s%%)"
  - now: "Battery %s%%; the limit is off: it charges to 100%%"
- Changed in `packs/core/charge-limit/status.sh:24`
  - was: "Charging to 100%% once (now %s%%), then stopping at %s%% again"
  - now: "Battery %s%%; charging to 100%% once, then stopping at %s%% again"
- Changed in `packs/core/charge-limit/status.sh:31`
  - was: "Not charging until the battery is below %s%% (now %s%%)"
  - now: "Battery %s%%; not charging until it's below %s%%"
- Changed in `packs/core/charge-limit/status.sh:32`
  - was: "Holding at %s%% (battery %s%%, not charging)"
  - now: "Battery %s%%; holding at the %s%% limit, not charging"
- New in `packs/core/charge-limit/status.sh:37`
  - now: "Battery %s%%; charging stops at %s%%"
