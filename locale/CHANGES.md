# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-10
- Changed in `gui/apply_changes.py:292`
  - was: "SteamOS was updated ({old} → {new}), and these tweaks need attention since: {tweaks}."
  - now: "SteamOS was updated ({old} → {new})."
- New in `gui/apply_changes.py:294`
  - now: "Broken since, Repair installs again: {tweaks}."
- New in `gui/apply_changes.py:297`
  - now: "Not Repair's to fix, their status says what each needs (↻ Reinstall, a restart): {tweaks}."
- New in `packs/core/adb-scrcpy/phone:345`
  - now: "ended by the system: signal %s"
- New in `packs/core/adb-scrcpy/phone:347`
  - now: "exit status %s"
- Changed in `packs/core/adb-scrcpy/phone:439`
  - was: "scrcpy stopped straight away. It said:\n\n%s\n\nIf the phone asked to allow USB debugging or screen sharing, allow it and try again."
  - now: "scrcpy stopped straight away (%s). It said:\n\n%s\n\nIf the phone asked to allow USB debugging or screen sharing, allow it and try again. Its whole output: %s"
- New in `packs/core/bt-music-only/README.md`
  - now: "Bluetooth headphones and earbuds connect for music (A2DP) only, without the call profile"
- New in `packs/core/bt-music-only/README.md`
  - now: "Bluetooth headphones: music only"
- New in `packs/core/bt-music-only/README.md`
  - now: "The Frame stops offering Bluetooth audio devices the hands-free and headset profiles (the ones with a microphone and a voice channel). Headphones and earbuds then connect for music (A2DP) only, and stay on that profile. Their microphone isn't used; SteamVR uses the Frame's own."
- New in `packs/core/bt-music-only/install.sh:10`
  - now: "Installed; applies when the Frame restarts (SteamVR is using the sound system now)."
- New in `packs/core/bt-music-only/install.sh:12`
  - now: "Bluetooth headphones now connect for music only (A2DP). Reconnect ones connected already."
- New in `packs/core/bt-music-only/install.sh:14`
  - now: "Installed; applies when the Frame restarts."
- New in `packs/core/bt-music-only/status.sh:11`
  - now: "Applies when WirePlumber restarts: restart the Frame, or ↻ Reinstall with SteamVR closed"
- New in `packs/core/bt-music-only/status.sh:15`
  - now: "A connected device still offers its call profile: reconnect it, or restart the Frame"
- New in `packs/core/bt-music-only/status.sh:17`
  - now: "Bluetooth headphones connect for music only (A2DP)"
- New in `packs/core/bt-music-only/uninstall.sh:10`
  - now: "The call profiles are back; reconnect headphones connected already."
- New in `packs/core/bt-music-only/uninstall.sh:12`
  - now: "The call profiles are back when the Frame restarts."
- New in `packs/core/bt-music-only/uninstall.sh:8`
  - now: "The call profiles are back when the Frame restarts (SteamVR is using the sound system now)."

## 2026-11-18
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "1 hour (the default)"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "10 minutes"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "15 minutes (the default)"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "5 minutes"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "A small background service watches for the headset going into standby (SteamVR does that a short while after it comes off your head). After 15 minutes of standby on battery, or 60 plugged in, it puts the Frame to sleep, as a short press of the power button does."
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "How long the headset stays in standby (off your head) before the Frame goes to sleep. The wait starts again each time it wakes."
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "No"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "On battery, sleep after"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "Plugged in, sleep after"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "Puts the Frame to sleep once the headset has been off your head a while, so it doesn't run flat on a shelf"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "Sleep even while someone is logged in over SSH"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "Sleep when idle in VR"
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "Yes"
- New in `packs/bugfixes/auto-sleep/install.sh:13`
  - now: "The Frame now sleeps once the headset has been in standby a while: %s"
- New in `packs/bugfixes/auto-sleep/status.sh:5`
  - now: "service not running (%s)"
- New in `packs/core/bt-music-only/README.md`
  - now: "With both profiles on offer, a pair of earbuds is connected on the call profile too, with its voice channel open. When the Frame goes to sleep, that channel is torn down mid-stream, and some earbuds then never answer the Frame again until they're reset and paired anew. The music profile alone reconnects cleanly. The Frame's own microphone is what SteamVR uses anyway, so the call profile gives nothing in VR."

## 2026-11-21
- New in `packs/bugfixes/auto-sleep/README.md`
  - now: "Steam's own \"Sleep after\" setting (Settings → Power) doesn't fire in the Frame's VR session: on SteamOS 0.5.8 and 0.5.9 a Frame left in standby stayed awake for hours with it set to 15 minutes on battery, losing about 20% an hour, and one ran from full to 2% on a shelf."

## 2026-11-25
- New in `gui/packs_page.py:392`
  - now: "Stop using all"
- New in `gui/packs_page.py:393`
  - now: "Every pack that isn't Frame Tweaks' own leaves the list, with its tweaks; installed ones stay until you uninstall them"
- New in `gui/packs_page.py:396`
  - now: "Yes, trust %d pack"
  - plural: "Yes, trust all %d packs"
- New in `gui/packs_page.py:398`
  - now: "Trust all…"
- New in `gui/packs_page.py:399`
  - now: "Use every pack that isn't Frame Tweaks' own, as its files are now: their tweaks join the list, and the ones you tick run as you, with your files and passwords in reach. Trust only packs from people you trust. Asks once more before it does."
- New in `lib/userpacks.py:272`
  - now: "Every pack that isn't Frame Tweaks' own is trusted already."
- New in `lib/userpacks.py:273`
  - now: "No pack that isn't Frame Tweaks' own is in use."
