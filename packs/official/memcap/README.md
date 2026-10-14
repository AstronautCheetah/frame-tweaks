---
title: Memory caps
emoji: 🧮
category: System
tier: core
summary: >-
  Memory limits for heavy apps (Whisper, Android Mirror, VSCodium) so one can't freeze the
  headset
what: >-
  Memory limits for Whisper (dictation), scrcpy (Android Mirror) and VSCodium, adjustable in one
  file.
why: >-
  One runaway app can use up the Frame's memory and stall VR. With a limit, only that app slows
  down or stops; the rest of the headset keeps running.
author: Frame Tweaks
source:
  relation: idea from
  url: https://github.com/Jovian-Experiments/Jovian-NixOS
icon: {theme: memory}
changes: >-
  `~/.local/bin/capped`, `~/.config/frame-tweaks/memcap.conf`, a systemd drop-in for VSCodium's
  Flatpak scope
access: Starts capped apps in their own systemd scope
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall memcap` (keeps your limits file)"
test:
  offline: true
  keeps: [".config/frame-tweaks/memcap.conf"]
---
# Memory caps

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Memory limits for Whisper (dictation), scrcpy (Android Mirror) and VSCodium, adjustable in one file.

**Why on a Steam Frame:** One runaway app can use up the Frame's memory and stall VR. With a limit, only that app slows down or stops; the rest of the headset keeps running.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install memcap
```

Nothing else to do: each app gets its limit the next time it starts.

## Settings
The limits are in `~/.config/frame-tweaks/memcap.conf` (units `K`, `M`, `G`):

| App | Slowed down above | Stopped at |
|---|---|---|
| Whisper ([Dictation](../dictation/)) | 2 GB | 3 GB |
| scrcpy ([Android Mirror](../adb-scrcpy/)) | 1 GB | 2 GB |
| VSCodium | 3 GB | 5 GB |

Above the first limit, the system slows the app down and takes back some of its memory. At the
second, it stops the app; everything else keeps running.

To change them, edit the file (for example `nano ~/.config/frame-tweaks/memcap.conf`). Whisper
and scrcpy use the new limits the next time they start. For VSCodium, run
`./install.sh install memcap` again after editing, then restart VSCodium.

## How it works
- `capped <profile> -- command` runs a command in its own systemd scope (a group of processes
  that systemd can limit), with that profile's `MemoryHigh` and `MemoryMax`. Dictation and
  Android Mirror start their programs through it when it's installed. If systemd can't be
  reached, the command runs without a limit.
- Flatpak apps already get their own scope (`app-flatpak-<id>-<pid>.scope`), so VSCodium's
  limit is a systemd drop-in that applies to every scope with that name prefix.
- No root is needed: your own systemd user manager applies the limits.

## Good to know
- Only these three apps are capped. Most other apps on the Frame run inside Steam's own session,
  so they can't be capped one by one.
- The limits need systemd to hand the memory controller to user services. The status line warns
  if it doesn't, and `./install.sh check-system` checks it too.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/capped`, `~/.config/frame-tweaks/memcap.conf`, a systemd drop-in for VSCodium's Flatpak scope
- **Unusual access:** Starts capped apps in their own systemd scope
- **Undo:** `./install.sh uninstall memcap` (keeps your limits file)
<!-- /generated:changes -->

## Credits
Idea from [Jovian-NixOS](https://github.com/Jovian-Experiments/Jovian-NixOS)'s early
out-of-memory handling; this is a home-folder-only take using systemd's per-scope limits.
See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status memcap` · Remove: `./install.sh uninstall memcap`
