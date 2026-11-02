---
title: VR memory guard
emoji: 🛡️
category: System
tier: core
summary: >-
  Keeps memory free for SteamVR, so a runaway Flatpak app such as Firefox is stopped instead of
  VR crashing
what: >-
  Flatpak apps (Firefox and others from Discover) together always leave 5 GB for SteamVR, Steam
  and your game; Firefox gets a 5 GB limit of its own; and when memory runs out anyway, SteamVR
  is the last thing stopped.
why: >-
  The Frame's 16 GB is shared by VR and every app you open. When one app takes it all (signing
  in to Firefox can install all your extensions at once and take 10 GB), the whole headset
  stalls and SteamVR's compositor can crash, dropping you out of VR.
author: Frame Tweaks
icon: {theme: security-high}
changes: >-
  `~/.config/frame-tweaks/vr-memory-guard.conf`, and systemd drop-ins for your Flatpak apps,
  Firefox and SteamVR in `~/.config/systemd/user/`
access: Sets memory limits on your own systemd services (no root)
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall vr-memory-guard` (keeps your limits file)"
test:
  offline: true
  keeps: [".config/frame-tweaks/vr-memory-guard.conf"]
---
# VR memory guard

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Flatpak apps (Firefox and others from Discover) together always leave 5 GB for SteamVR, Steam and your game; Firefox gets a 5 GB limit of its own; and when memory runs out anyway, SteamVR is the last thing stopped.

**Why on a Steam Frame:** The Frame's 16 GB is shared by VR and every app you open. When one app takes it all (signing in to Firefox can install all your extensions at once and take 10 GB), the whole headset stalls and SteamVR's compositor can crash, dropping you out of VR.
<!-- /generated:intro -->

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install vr-memory-guard
```

The limits apply at once to apps already open. SteamVR takes its place in the queue the next
time it starts.

## What it does
- **Flatpak apps leave a reserve for VR.** Every Flatpak app (Firefox, and the apps you
  install from Discover) shares one limit: the Frame's memory minus 5 GB. If they reach it, the
  app that asks for more is stopped; SteamVR, Steam and your game keep running.
- **Firefox has its own limit (5 GB).** Above it, Firefox stops one of its processes (a tab
  shows "Gah. Your tab just crashed.", or Firefox closes) before anything else is affected.
- **SteamVR is stopped last.** If memory runs out anyway, the kernel picks an app before
  SteamVR.

**Not limited:** games you start from Steam, and the desktop itself with its own programs
(Discover, Konsole, Dolphin and the like). They run in Steam's session, with SteamVR, and how
much memory they need is up to Valve and the game's developers.

## Settings
The limits are in `~/.config/frame-tweaks/vr-memory-guard.conf` (sizes in `M` or `G`):

| Setting | Default | Meaning |
|---|---|---|
| `reserve_for_vr` | 5G | Memory Flatpak apps leave free for VR |
| `apps_swap_max` | 2G | How much of their memory may go to swap |
| `firefox_max` | 5G | Firefox's own limit |
| `firefox_swap_max` | 1G | Firefox's swap on top of that |

After editing (for example `nano ~/.config/frame-tweaks/vr-memory-guard.conf`), run
`./install.sh install vr-memory-guard` again.

## How it works
- Each Flatpak app runs in its own systemd scope (`app-flatpak-<id>-<number>.scope`), in the
  slice `app.slice`. A few small background services share that slice and its limit (SteamOS's
  manager and portals, Frame Tweaks' VR dashboard helper); everything else, Steam and its games
  included, runs in `session.slice`, which isn't limited. A drop-in gives the slice a `MemoryMax`, and one for
  the scope name prefix `app-flatpak-org.mozilla.firefox-` gives every Firefox its own. Install
  also sets the running slice and Firefox at once (`systemctl --user set-property --runtime`),
  because a running slice doesn't take a new drop-in until the next login.
- There's no `MemoryHigh`. With it, the kernel slows an app down instead of stopping it, and in
  tests on a Frame a runaway app went on crawling for minutes. `MemorySwapMax` stops it growing
  into swap instead.
- SteamVR's service gets `OOMScoreAdjust=100`. Apps run at 200, and 100 is the lowest a user's
  own service may set.
- No root: your own systemd user manager applies all of it.

## Good to know
- **Signing in to Firefox** can install all your synced extensions at once. With this tweak,
  Firefox may close during that; open it again and the rest install. To avoid it, turn off
  syncing add-ons for this device (Firefox Settings → Sync).
- An app that genuinely needs more (a big video edit, say) is stopped at the limit: raise
  `firefox_max` or lower `reserve_for_vr`.
- The limits need systemd to hand the memory controller to your services, as SteamOS does on
  the Frame. The status line warns if it doesn't, and `./install.sh check-system` checks it.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.config/frame-tweaks/vr-memory-guard.conf`, and systemd drop-ins for your Flatpak apps, Firefox and SteamVR in `~/.config/systemd/user/`
- **Unusual access:** Sets memory limits on your own systemd services (no root)
- **Undo:** `./install.sh uninstall vr-memory-guard` (keeps your limits file)
<!-- /generated:changes -->

---
Check: `./install.sh status vr-memory-guard` · Remove: `./install.sh uninstall vr-memory-guard`
