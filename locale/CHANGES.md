# English text changes to translate

`dev/i18n.py extract` adds to this each time it refreshes the template: each text that's new, or
whose English changed, with where it is (as of that change) and, for a changed one, what it was.
An entry goes by itself once every language has its text translated (`dev/i18n.py update`,
`import`): what's here is the translation work waiting for the next release (`dev/i18n.py todo`).
`dev/i18n.py export` hands translators what a changed text was, and its old translation, to
adjust. Texts are JSON strings (`\n` is a new line). Don't edit by hand.

## 2026-11-10
- New in `packs/core/bt-music-only/README.md`
  - now: "Bluetooth headphones and earbuds connect for music (A2DP) only, without the call profile"
- New in `packs/core/bt-music-only/README.md`
  - now: "Bluetooth headphones: music only"
- New in `packs/core/bt-music-only/README.md`
  - now: "The Frame stops offering Bluetooth audio devices the hands-free and headset profiles (the ones with a microphone and a voice channel). Headphones and earbuds then connect for music (A2DP) only, and stay on that profile. Their microphone isn't used; SteamVR uses the Frame's own."
- New in `packs/core/bt-music-only/README.md`
  - now: "With both profiles on offer, a pair of earbuds is connected on the call profile too, with its voice channel open. When the Frame goes to sleep, that channel is torn down mid-stream, and some earbuds (Bose QuietComfort Earbuds II here) never answer the Frame again until they're reset and paired anew. The music profile alone reconnects cleanly. The Frame's own microphone is what SteamVR uses anyway, so the call profile gives nothing in VR."
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
