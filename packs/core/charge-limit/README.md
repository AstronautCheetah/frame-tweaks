---
title: Battery charge limit
emoji: 🔋
category: Hardware
tier: core
summary: Stop charging at 80% (or 74 to 90%) while the Frame is on, for a battery that wears more slowly
what: >-
  Charging stops when the battery reaches the limit you choose (80% unless you change it) and
  starts again 1% below it, so the battery stays within 1% of the limit. Plugged in, the Frame
  then runs mostly from the charger or power bank. Charge to 100% once, in its settings, lifts
  the limit until the next full charge.
why: >-
  A lithium-ion battery wears faster when it's kept full, as it is when the Frame spends a lot
  of time plugged in, a power bank in your pocket while you play, say. SteamOS offers a charge
  limit on the Steam Deck (Settings → Power), but not on the Frame.
author: Frame Tweaks
sudo: >-
  once, to add a udev rule that lets you pause the battery's charging, and again to remove
  it
experimental: >-
  Uses the Frame's charger driver directly (its charging pause switch). SteamOS's charger
  service turns the pause off each time it starts; it's on again within 30 seconds. The status
  says if the switch is gone, or if the battery still charges while paused.
icon: {theme: battery-080}
processes: [~/.local/bin/charge-limit --run, ~/.local/bin/charge-limit-sleep]
settings:
  file: ~/.config/frame-tweaks/charge-limit.conf
  format: shell
  about: >-
    Charging stops at this level and starts again 1% below it. Plugged in at the limit, the Frame
    runs mostly from the charger or power bank. A lower limit wears the battery a little less. The
    level is the battery's own reading, as KDE shows it; Steam's dashboard shows a higher figure for
    the same charge (about 8 points more around 80%: 78% here is 86% there).
  note: >-
    Applies within 30 seconds.
  options:
    - key: CHARGE_LIMIT
      title: Stop charging at
      default: "80"
      choices:
        - {label: "74%", value: "74"}
        - {label: "76%", value: "76"}
        - {label: "78%", value: "78"}
        - {label: "80% (the default)", value: "80"}
        - {label: "85%", value: "85"}
        - {label: "90%", value: "90"}
        - {label: "Off (charge to 100%)", value: "off"}
  actions:
    - label: Charge to 100% once
      script: full-once.sh
      about: >-
        Before a long session away from power: the limit is lifted until the battery is full (or
        the Frame restarts), then applies again. You don't need it otherwise.
changes: >-
  `charge-limit` and `charge-limit-sleep` in `~/.local/bin` and its user service; a udev rule
  (`/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules`, kept by SteamOS updates through
  `/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf`) that makes the charger's pause
  switch yours each time the Frame starts
access: >-
  Pauses and resumes the battery's charging. Asks for your sudo password once to add the udev
  rule, and again to remove it
survives_updates: Yes (SteamOS updates keep the udev rule)
undo: >-
  `./install.sh uninstall charge-limit` (asks for your sudo password to remove the udev rule);
  the battery charges normally again
---
# Battery charge limit

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
Charging stops when the battery reaches the limit you choose (80% unless you change it) and starts again 1% below it, so the battery stays within 1% of the limit. Plugged in, the Frame then runs mostly from the charger or power bank. Charge to 100% once, in its settings, lifts the limit until the next full charge.

**Why on a Steam Frame:** A lithium-ion battery wears faster when it's kept full, as it is when the Frame spends a lot of time plugged in, a power bank in your pocket while you play, say. SteamOS offers a charge limit on the Steam Deck (Settings → Power), but not on the Frame.
<!-- /generated:intro -->

> **According to Valve Support:** For normal daily use, it's fine to leave the Frame connected
> to power, including when the battery is at 100%. The battery manages this automatically and
> won't keep trying to charge past full or overcharge itself. For longer-term storage, Valve
> recommend shutting the Frame down through the OS and leaving it unplugged. You also don't need
> to routinely discharge the battery to 10-15% before charging it again.

So you don't need this tweak to keep the battery safe. It's for a battery that wears more
slowly: a lithium-ion battery ages faster the longer it sits full, and a Frame that's often
plugged in (to a power bank while you play, say) sits full a lot.

## Install
Tick it in the Frame Tweaks window, or:

```sh
./install.sh install charge-limit
```

The charger's pause switch belongs to root, so the install asks for your **sudo password**
once. It adds a udev rule that makes that one switch yours each time the Frame starts, the way
SteamOS's own rule makes the LEDs yours (`99-leds.rules`). Uninstalling asks for it again, to
remove the rule. If your user has no password yet, set one first with `passwd` in Konsole.

## Use
- **The limit:** ⚙ Settings on its row (or `./install.sh settings charge-limit`): 74%, 76%, 78%,
  80% (the default), 85%, 90% or Off. A lower limit wears the battery a little less. It applies
  within 30 seconds.
- **Charge to 100% once**, a button on the same page, is only for a long session away from
  power: the limit is lifted until the battery is full (or the Frame restarts), then applies
  again. You don't need it otherwise.
- **Its status** shows the limit and the battery level, and "not charging" while it holds.

## Good to know
- **Steam shows a higher figure.** The limit, KDE and Frame Tweaks all go by the battery's own
  fuel gauge (`/sys/class/power_supply/*/capacity`). Steam's dashboard (SteamVR's battery level)
  shows its own conversion of that reading, about 8 points more around 80% (measured 74→82 up to
  78→86), so with the limit at 78% Steam shows about 86% when charging stops. That's expected.
- **Asleep, the limit can't be checked,** so as the Frame goes to sleep, charging pauses if the
  battery is within 10% of the limit (or over it): it doesn't charge past it overnight. Lower
  than that, it charges on while asleep, so a nearly empty Frame isn't left low, and may go past
  the limit; once awake, the limit applies again. Switched off, the Frame charges to 100% as
  before.
- **Plugged in at the limit,** the Frame runs mostly from the charger or power bank, but the
  battery still drains slowly: on a Frame plugged into a 45 W USB-C charger, holding at 80%, the
  battery gave about 1 W (it went from 84% to 79% in 45 minutes). Charging starts again 1% below
  the limit, so at 80% the battery goes back and forth between 79% and 80%: charging for a few
  minutes about every ten. Swings that small add little wear (see "For maintainers").
- **Desktop mode's battery icon says the charger is too weak; it isn't.** While the limit holds,
  KDE's battery icon in desktop mode shows something like:

  > Battery at 82%, plugged in but still discharging
  >
  > The power supply is not powerful enough to charge the battery

  That's this tweak pausing the charging, not your charger: KDE only sees that power is plugged
  in and the battery isn't charging, and guesses why. Each time the battery is 1% below the
  limit, it charges again for a few minutes and the message goes away until it's paused again.
- **It doesn't drain a full battery to the limit:** plugged in at 100%, it stays at 100% until
  you use it on battery.
- **Valve's own setting comes first.** If SteamOS adds a charge limit for the Frame (Steam →
  Settings → Power, as on the Steam Deck), use that instead: this tweak's status says so when it
  appears, and Frame Tweaks will drop this tweak in favour of Valve's.

## How it works
- `charge-limit --run` (a user service) checks the battery every 30 seconds. At the limit it
  sets the charger's pause switch
  (`/sys/class/power_supply/pm8550b-charger/charging_pause`), and 1% below it clears it again.
  It never changes the charger's voltage or current, and it lifts only a pause it made itself.
- `charge-limit-sleep`, which the service starts, holds a *delay* sleep lock from logind (as
  SteamVR's own services do). When the Frame is about to sleep, logind gives it a moment to run
  `charge-limit --before-sleep` (the pause near the limit), then the Frame sleeps; as it wakes,
  it checks again at once. Before it, a Frame that went to sleep during one of the few minutes
  of charging charged on to 100% overnight.
- SteamOS's charger service (`deckard-charger`) clears the switch each time it starts; the next
  check sets it again. Stopping the service (uninstalling, or shutting down) clears it, so
  charging is never left paused.
- The udev rule is the only part outside your home folder:
  `/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules`, listed in
  `/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf` so that SteamOS updates keep it.

## For maintainers
Remove this tweak once SteamOS has a charge limit for the Frame, in favour of Valve's. Its
status checks for it: SteamOS Manager's device file for the Frame
(`/usr/share/steamos-manager/devices/steam-frame.toml`) gaining a `[battery_charge_limit]`
section, as the Steam Deck's has, which puts the setting in Steam's Settings → Power.

**Why it can't hold the battery still.** Paused, the battery still gives part of the Frame's
power (about 1.7 W on a 45 W charger), and the charger's other controls (`charging_enable`,
`constant_charge_current`) are accepted but ignored on SteamOS 0.5.6: the pause is the only
control that works. **Why it resumes 1% below the limit (5% before October 2026):** the drain is
the same either way, so the band only sets the swings and the average charge; studies of
micro-cycles find small swings add little wear and the average matters more, hence also the 74
to 78% limits. The measurements, the studies and when to test again are in
[docs/research/battery-charge-limit.md](../../../docs/research/battery-charge-limit.md), and
`sudo bash dev/charge-hold-test.sh` repeats the charger test.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (SteamOS updates keep the udev rule)
- **Changes:** `charge-limit` and `charge-limit-sleep` in `~/.local/bin` and its user service; a udev rule (`/etc/udev/rules.d/90-frame-tweaks-charge-limit.rules`, kept by SteamOS updates through `/etc/atomic-update.conf.d/frame-tweaks-charge-limit.conf`) that makes the charger's pause switch yours each time the Frame starts
- **🧪 Experimental:** Uses the Frame's charger driver directly (its charging pause switch). SteamOS's charger service turns the pause off each time it starts; it's on again within 30 seconds. The status says if the switch is gone, or if the battery still charges while paused.
- **Unusual access:** Pauses and resumes the battery's charging. Asks for your sudo password once to add the udev rule, and again to remove it
- **Undo:** `./install.sh uninstall charge-limit` (asks for your sudo password to remove the udev rule); the battery charges normally again
<!-- /generated:changes -->

## Credits
[y0usaf/frame-charge](https://github.com/y0usaf/frame-charge) showed that the Frame's charger
has this pause switch and holds the battery the same way (as root, from `/etc`). We wrote our own
rather than link it: it has no licence yet, and it says it hasn't been tried on real charging.
See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status charge-limit` · Remove: `./install.sh uninstall charge-limit`
