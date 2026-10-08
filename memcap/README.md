# Memory caps

Heavy apps get a memory limit, so one runaway process can't use up the Frame's memory and
stall VR: **Whisper** (dictation), **scrcpy** (Android Mirror) and **VSCodium**.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `~/.local/bin/capped`, `~/.config/frame-tweaks/memcap.conf`, a systemd drop-in for VSCodium's Flatpak scope
> - **Unusual access:** Starts capped apps in their own systemd scope
> - **Undo:** `./install.sh uninstall memcap` (keeps your limits file)
<!-- /generated:glance -->

```sh
./install.sh memcap
nano ~/.config/frame-tweaks/memcap.conf     # adjust the limits
```

| App | Slowed down above | Stopped at |
|---|---|---|
| Whisper | 2 GB | 3 GB |
| scrcpy | 1 GB | 2 GB |
| VSCodium | 3 GB | 5 GB |

Above the first limit the kernel slows the app and reclaims its memory; at the second it's
stopped (the rest of the headset keeps running). Changes apply the next time the app starts
(VSCodium: re-run `./install.sh memcap` after editing).

## How it works
- `capped <profile> -- command` runs a command in its own systemd scope with that profile's
  `MemoryHigh` / `MemoryMax`. Dictation and Android Mirror use it automatically when it's
  installed.
- Flatpak apps already get their own scope (`app-flatpak-<id>-<pid>.scope`), so VSCodium's
  limit is a systemd drop-in for every scope with that prefix.
- Most other apps on the Frame run inside Steam's own session service, so they aren't capped
  individually. `./install.sh check-system` confirms the memory controller is available.

## Credits
Idea from [Jovian-NixOS](https://github.com/Jovian-Experiments/Jovian-NixOS)'s early
out-of-memory handling; this is a home-folder-only take using systemd's per-scope limits.
See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status memcap` · Remove: `./install.sh uninstall memcap`
