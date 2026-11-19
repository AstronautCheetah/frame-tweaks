---
title: Sleep when idle in VR
emoji: 💤
category: System
tier: core
summary: Puts the Frame to sleep once the headset has been off your head a while, so it doesn't run flat on a shelf
what: >-
  A small background service watches for the headset going into standby (SteamVR does that a
  short while after it comes off your head). After 15 minutes of standby on battery, or 60
  plugged in, it puts the Frame to sleep, as a short press of the power button does.
why: >-
  Steam's own "Sleep after" setting (Settings → Power) doesn't fire in the Frame's VR session: on
  SteamOS 0.5.8 a Frame left in standby stayed awake for hours with it set to 15 minutes on
  battery, losing about 20% an hour, and one ran from full to 2% on a shelf.
author: Frame Tweaks
icon: {theme: system-suspend}
changes: >-
  `~/.local/bin/frame-tweaks-auto-sleep`, user service `frame-tweaks-auto-sleep`
access: Puts the Frame to sleep (as the power button does; no root)
survives_updates: Yes (everything is in your home folder)
undo: "`./install.sh uninstall auto-sleep`"
test: {offline: true}
processes: [~/.local/bin/frame-tweaks-auto-sleep]
settings:
  file: ~/.config/frame-tweaks/auto-sleep.conf
  format: shell
  about: >-
    How long the headset stays in standby (off your head) before the Frame goes to sleep. The
    wait starts again each time it wakes.
  note: >-
    Applies within 30 seconds.
  options:
    - key: AUTO_SLEEP_BATTERY
      title: On battery, sleep after
      default: "15"
      choices:
        - {label: "5 minutes", value: "5"}
        - {label: "10 minutes", value: "10"}
        - {label: "15 minutes (the default)", value: "15"}
        - {label: "30 minutes", value: "30"}
        - {label: "1 hour", value: "60"}
        - {label: "Never", value: "0"}
    - key: AUTO_SLEEP_PLUGGED
      title: Plugged in, sleep after
      default: "60"
      choices:
        - {label: "15 minutes", value: "15"}
        - {label: "30 minutes", value: "30"}
        - {label: "1 hour (the default)", value: "60"}
        - {label: "2 hours", value: "120"}
        - {label: "Never", value: "0"}
    - key: AUTO_SLEEP_SSH
      title: Sleep even while someone is logged in over SSH
      checkbox: true
      default: "no"
      choices:
        - {label: "Yes", value: "yes"}
        - {label: "No", value: "no"}
---
# Sleep when idle in VR

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
A small background service watches for the headset going into standby (SteamVR does that a short while after it comes off your head). After 15 minutes of standby on battery, or 60 plugged in, it puts the Frame to sleep, as a short press of the power button does.

**Why on a Steam Frame:** Steam's own "Sleep after" setting (Settings → Power) doesn't fire in the Frame's VR session: on SteamOS 0.5.8 a Frame left in standby stayed awake for hours with it set to 15 minutes on battery, losing about 20% an hour, and one ran from full to 2% on a shelf.
<!-- /generated:intro -->

## Install

Tick it in the Frame Tweaks window, or:

```sh
./install.sh install auto-sleep
```

It starts at once and with every login after.

## Use

Take the headset off and put it down: once SteamVR has put it in standby and the wait has passed,
the Frame sleeps. Wake it with the power button, as usual. Its status line says what it would do
now and why, for example "headset in standby 4 min, on battery: sleeps after 15 min; in 11 min".

## Settings

In the Frame Tweaks window, **⚙ Settings** on its row, or in `~/.config/frame-tweaks/auto-sleep.conf`:

| Setting | Default | Meaning |
|---|---|---|
| `AUTO_SLEEP_BATTERY` | 15 | Minutes of standby on battery before it sleeps (0: never) |
| `AUTO_SLEEP_PLUGGED` | 60 | The same, plugged in (0: never) |
| `AUTO_SLEEP_SSH` | no | `yes`: sleep even while someone is logged in over SSH |

## How it works

- **Standby is SteamVR's call.** SteamVR logs the headset (device 0) entering and leaving standby
  in `~/.local/share/Steam/logs/vrserver.txt`; the service reads the last of those every 30
  seconds. The wait counts from when it entered standby, or from the last wake if that was later.
- **It doesn't sleep** while SteamVR isn't running (desktop mode keeps KDE's own power settings),
  while the headset is in use, while someone is logged in over SSH (unless you allow it), or while
  a program holds a block on sleep (a backup or an update, as `systemd-inhibit --list` shows them).
- **On battery or not** comes from SteamOS's charger service (`/run/deckardcharger/ac_status`). A
  charger that has lost its power counts as unplugged, since the headset can't tell the two apart.
- **The sleep itself** is `systemctl suspend`, the same as a short press of the power button: Steam
  and SteamVR get the usual notice and get ready for it.

## Good to know

- Steam's "Sleep after" settings stay as they are; if a SteamOS update makes them work in VR,
  whichever comes first puts the Frame to sleep, and this tweak can go.
- The wait starts once SteamVR has put the headset in standby, which itself takes a little while
  after it comes off your head.
- See [docs/research/idle-sleep.md](../../../docs/research/idle-sleep.md) for what was measured.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder)
- **Changes:** `~/.local/bin/frame-tweaks-auto-sleep`, user service `frame-tweaks-auto-sleep`
- **Unusual access:** Puts the Frame to sleep (as the power button does; no root)
- **Undo:** `./install.sh uninstall auto-sleep`
<!-- /generated:changes -->

---
Check: `./install.sh status auto-sleep` · Remove: `./install.sh uninstall auto-sleep`
