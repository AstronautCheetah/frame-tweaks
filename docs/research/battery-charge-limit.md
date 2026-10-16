# Battery charge limit: research and decisions

For maintainers and reviewers; not shown in the app. What was measured on a Frame and read in
the literature before deciding how [Battery charge limit](../../packs/core/charge-limit/)
holds the battery, so the decisions can be checked again when SteamOS or the hardware changes.
The tweak's README has the short version (*Good to know*, *For maintainers*).

Measured on 15–16 October 2026 on one Frame: SteamOS 0.5.6 beta (build 20261015.6141207),
kernel 6.18.0-g83913f38113c, `deckard-charger` 20260928.1-1, battery 8 cycles old, plugged into
a 45 W USB-C charger.

## Decisions

| Decision | Why (sections below) |
|---|---|
| Hold the limit with the charger's pause switch, `charging_pause`, made the user's by a udev rule | It's the only control that changes anything; `charging_enable` and `constant_charge_current` are accepted but ignored ([The charger's controls](#the-chargers-controls)) |
| Accept that the battery drains slowly while paused | Paused, it gives 0.14–0.4 A whatever the charger can supply; no control holds it still ([Paused vs charging](#paused-vs-charging)) |
| Resume 1% below the limit (5% before) | The drain is the same either way; the band only sets the swing and the average charge, and small swings add little wear ([The literature](#the-literature), [Applying it](#applying-it-to-the-frame)) |
| Offer 74, 76 and 78% besides 80, 85, 90% and Off; keep 80% the default | The average charge matters more than the swing, so lower limits are worth offering; 80% stays the default as the common recommendation |
| Leave QPH2 and Valve's charger service alone | The charging mode where the current setting goes unused is managed by Valve's service; working against it risks more than it gains |
| Explain KDE's "power supply is not powerful enough" in the README | KDE sees power plugged in and the battery discharging, and guesses a weak charger; it's the pause |

## The hardware

From `/sys/class/power_supply` on the Frame:

| | |
|---|---|
| Battery (fuel gauge `max1720x_bat_7-36`, linked by SteamOS as `/run/deckardcharger/BAT0`) | 2 cells in series: `voltage_max_design` 7.76 V (3.88 V per cell), `voltage_min_design` 6.6 V; `charge_full_design` 2.730 Ah, `charge_full` 2.578 Ah |
| Charger (`pm8550b-charger`, driver `qcom_pm8550b_charger`, built into Valve's kernel) | `constant_charge_voltage` 8.80 V (4.40 V per cell); `constant_charge_current` 1.0 A (max 1.2 A); writable controls `charging_pause`, `charging_enable`, `constant_charge_current` and others, all root's (`charging_pause` is the user's through the tweak's udev rule) |
| USB-C | PD contract 15 V × 3 A (45 W) |

Valve's spec page lists a "Rechargeable 21.6 Wh Li-ion battery"; iFixit's teardown found a
two-cell lithium-polymer pack rated 20.9 Wh. Neither names the chemistry. A 3.88 V nominal and
4.40 V full charge per cell is typical of high-voltage LiCoO₂ (LCO) on graphite, the usual
chemistry in phones and headsets: **likely, not confirmed**.

`deckard_charge_daemon` (Valve's charger service) writes `charging_pause` only as it starts (to
0). Its strings show it manages a charging mode called QPH2 ("AICL Complete - Entering QPH2",
"Exiting QPH2 - Low Current and No Load", "Exiting QPH2 - USB Voltage Drop"), and it sets
charge current, voltage and input limits for another charger chip (`mp2652-charger`) that this
Frame doesn't have.

## Measurements

Battery current from the fuel gauge, `current_now`: positive is charging, negative is the
battery giving power. The battery is at about 8.3 V, so 0.2 A is about 1.7 W.

### Paused vs charging

Battery at 77%, the Frame in use, the switch flipped by hand (and put back):

| State | Battery current, 1 s apart |
|---|---|
| Paused | −353, −206, −158, −143 mA |
| Charging (`charging_pause=0`) | +706, +848, +753, +631, +338, +749, +577, +694, +761, +676, +598 mA |
| Paused again | −213, −177, −224, −275, −200 mA |

Over time: paused from 84% when the Frame started at 22:44, the battery was at 79% about 45
minutes later. Other samples while paused: −142 to −404 mA.

So the charger can carry the whole load and charge the battery at +0.6–0.85 A, but paused, the
battery still covers part of the load. Desktop mode's battery icon then says "plugged in but
still discharging … The power supply is not powerful enough to charge the battery".

### The charger's controls

Run as root (`dev/charge-hold-test.sh`), each state held for 14 s (first pass) or set, paused
3 s and resumed before 30 s of readings (second pass), at 76%:

| | Setting | Average | Range / readings |
|---|---|---|---|
| A | paused (what the tweak does) | −212 mA | −348 to −140 |
| B | `charging_enable=0` | +790 mA | +676 to +910 |
| C | `constant_charge_current` 0 mA (reads back 0) | +769 mA | +652 to +891 |
| C | 50 mA (reads back 50) | +775 mA | +682 to +900 |
| C | 100 mA (reads back 100) | +749 mA | +619 to +906 |
| D | charging as normal | +785 mA | +660 to +969 |
| E | 0 mA, after a pause and resume | +833 mA | 870, 946, 730, 741, 892, 818 |
| F | 100 mA, after a pause and resume | +811 mA | 798, 783, 799, 860, 895, 733 |
| G | `charging_enable=0`, after a pause and resume | +799 mA | 783, 913, 908, 737, 854, 599 |
| H | charging as normal | +1069 mA | 890, 734, 813, 1316, 1326, 1336 |

`status_detailed` meanwhile: `CC: 1`, `CV: 0`, `Buck: 1`, `Input OK: 1`, `USB Suspend: 0`,
`JEITA: 0`, `QPH VBAT1 OK: 1`, `QPH VIN OK: 1`, **`QPH2: 1`**; `aicl_status` 0, `charger_status`
131.

`charging_enable` and `constant_charge_current` are accepted (and read back as written) but
don't change the charging, at once or after a restart. The charger reports QPH2, a mode Valve's
service puts it in, so our reading is that the current setting isn't used in that mode. That is
an inference from these numbers: the driver's source isn't available. **The pause is the only
control that works, and no control holds the battery still.**

## The literature

What we looked for: whether small swings around a fixed charge (micro-cycles), here 1–5%, wear
a battery more than holding it, and how the swing and the average charge compare. Publisher
pages blocked fetching, so 1 and 3 are from their abstracts, highlights and citing papers; 2 is
from its open-access full text.

1. **Saxena, Hendricks, Pecht (2016)**, "Cycle life testing and modeling of graphite/LiCoO₂
   cells under different state of charge ranges", *J. Power Sources* 327, 394–400,
   [doi:10.1016/j.jpowsour.2016.07.057](https://doi.org/10.1016/j.jpowsour.2016.07.057)
   (University of Maryland, CALCE). Commercial graphite/LCO pouch cells (1.5 Ah), the Frame's
   likely chemistry, cycled at 1C over different SOC windows (such as 0–100%, 20–80%,
   20–100%) to 80% capacity. Capacity loss depends on the **mean SOC, the ΔSOC (swing) and the
   C-rate**; a power-law model is fitted. We couldn't read the per-window numbers.
2. **Soto, Berrueta, Mateos, Sanchis, Ursúa (2022)**, "Impact of micro-cycles on the lifetime
   of lithium-ion batteries: An experimental study", *J. Energy Storage* 55, 105343,
   [doi:10.1016/j.est.2022.105343](https://doi.org/10.1016/j.est.2022.105343),
   [open access](https://academica-e.unavarra.es/server/api/core/bitstreams/f40b81f9-30e2-4f4d-a89d-a077be9eddbc/content).
   Eight LG 18650HG2 cells (graphite + SiO anode, high-nickel NMC cathode, 3 Ah, 4.2 V), deep
   cycles with micro-cycles (defined as < 2% DOD) of 0.5, 1 or 2% superimposed, for over 3,000
   deep cycles. Micro-cycles had "a negligible, or even positive effect": counted in equivalent
   full cycles, cells with 0.5% micro-cycles lasted nearly 3,000 against no more than 1,500;
   counted in deep cycles alone, cells with and without micro-cycles aged about the same. 0.5%
   did best, and 1% better than 2%.
3. **Ćurić, Lohmann, Peis, Reichbauer, Bohlen (2026)**, "Influence of microcycles on the aging
   mechanisms of Li-ion cells", *J. Power Sources* 689, 240705,
   [doi:10.1016/j.jpowsour.2026.240705](https://doi.org/10.1016/j.jpowsour.2026.240705)
   (open access, CC BY). 18 NCA / silicon-carbon cells with microcycles of 2.5–5% DOD at a
   **constant mean SOC**, against cells only stored (calendar aging). Total capacity fade was
   nearly identical to storage, past 1,000 equivalent full cycles, though the mechanisms
   differed (more on the negative electrode); aging depended more on the C-rate than on the
   depth.

**Gaps:** no study found tests LCO at 1% swings; 2 and 3 use NMC and NCA with silicon in the
anode. No source quantified high-voltage (4.4 V) LCO's calendar aging at 75–80% against other
levels, though calendar aging rising with SOC is the general finding (1, and the storage
literature).

## Applying it to the Frame

The drain while paused doesn't depend on the band, so neither does the energy the battery
cycles: in a steady state, paused about 80% of the time at about −210 mA and charging the rest
at about +800 mA, it cycles roughly 0.17 Ah an hour, about 0.06 equivalent full cycles an hour,
or 1.5 a day plugged in all day (estimates from the currents above; the load varies). The band
sets only the swing and the average:

| Band | Swing | Average charge | Charging |
|---|---|---|---|
| 75–80% (before) | 5% | 77.5% | about 10 min every 47 |
| 79–80% (limit 80%) | 1% | 79.5% | about 2 min every 10 |
| 77–78% (limit 78%) | 1% | 77.5% | about 2 min every 10 |

From the literature, micro-cycles this small age a cell about like storing it at their average
charge (3), add almost no wear and less the smaller they are (2), and both a smaller swing and a
lower average slow LCO's fade (1). So **a 1% swing is slightly better than 5%, and the average
matters more**: a limit 2% lower with a 1% swing keeps the old average with smaller swings.
Both effects are small next to temperature and time spent at high charge. Hence 1% swings and
the 74, 76 and 78% limits.

## Sleep

Asleep, the service can't run, so whatever the switch is set to as the Frame goes to sleep holds
all night. On 16 October 2026, with a 78% limit and 1% swings, charging was turned back on at
77% at 00:53:13; the Frame slept from 00:59:22 to 06:33:41 (`PM: suspend entry (deep)` in the
system log) and woke at 99%. With small swings charging is on a few minutes at a time, so a
Frame that goes to sleep plugged in often catches it on.

Since then `charge-limit-sleep` holds a logind *delay* lock on sleep (the same kind SteamVR,
XRService and UPower hold on the Frame: `busctl --system call org.freedesktop.login1
/org/freedesktop/login1 org.freedesktop.login1.Manager ListInhibitors`), and on
`PrepareForSleep` pauses charging when the battery is within 10% of the limit or over it, then
releases the lock. Lower than that it lets the Frame charge while asleep, so a Frame put down
nearly empty isn't left low, at the cost of possibly going past the limit that night. Watching
the system bus with `busctl monitor` needs root; subscribing to the signal and taking the lock
don't.

## Revisit when

- **SteamOS gains a charge limit for the Frame** (`[battery_charge_limit]` in
  `/usr/share/steamos-manager/devices/steam-frame.toml`; the tweak's status checks): drop this
  tweak for Valve's, and see whether Valve's holds the battery still.
- **The charger driver or Valve's service changes** (a SteamOS update to `deckard-charger` or the
  kernel): run `sudo bash dev/charge-hold-test.sh` again. A control that brings the battery
  current near 0 while plugged in would allow a true hold, without micro-cycles.
- **The chemistry is confirmed** (a cell datasheet or a teardown naming it), or a study tests
  LCO at swings of about 1%.
