# The Frame doesn't sleep when idle in VR

Measured on a Steam Frame with SteamOS 0.5.8 (beta, build 20261106) until Nov 14, then 0.5.9 (build
20261113), with SteamVR 2.19, November 2026.
Behind the Sleep when idle in VR tweak (`packs/bugfixes/auto-sleep`).

## What happens

- **Steam has the settings, and they're on.** Steam → Settings → Power shows "When On Battery and
  Idle" and "When Plugged In and Idle", each with **Sleep after**. Steam's UI reads them as the
  client settings `system_idle_suspend_battery_sec` and `system_idle_suspend_ac_sec`; on this
  Frame they were 900 (15 min) and 3600 (60 min). The section is shown only in the gamescope
  session, which the Frame's VR session is (gamescope runs with `--backend openvr`).
- **They never fired.** `~/.local/share/Steam/logs/systemmanager.txt` logs every sleep Steam
  starts ("Issuing Suspend Command"); from Nov 3 to Nov 18 every one of them followed a press of
  the power button or Steam's Sleep entry, none an idle timeout:
  - Nov 14 21:02 to Nov 16 12:36: the headset in standby, plugged in, about 39 hours awake.
  - Nov 16 12:36 to 18:30: the same, after the charger lost its power: 100% to 2% in about 6 hours,
    then SteamOS's own low-battery power-off.
  - Nov 17 19:29 to Nov 18 11:07: in standby, plugged in, about 15.5 hours awake.
  - Nov 18 20:58 to 21:17: in standby since 20:36, on battery: still awake after 19 minutes, at
    about 1% every 3 minutes (about 20% an hour).
- **Nothing blocks sleep.** `systemd-inhibit --list` shows only *delay* locks (UPower,
  NetworkManager, SteamVR's `vrserver` "Driver standby", XRService, the DSP service) and
  PowerDevil's block on the power and lid keys, not on sleep. Sleeping by hand works and holds (53,
  24 and 16.6 hours), and logind's own idle action is off (`IdleAction=ignore`).
- **Standby is SteamVR's, and it's logged.** `vrserver.txt` has "0 - entering standby" and "0 -
  leaving standby" for the headset (device 0; 1 and 2 are the controllers), a short while after it
  comes off the head or goes back on.

Why Steam's idle timer doesn't fire in this session isn't known. The client has
`CSleepController::CheckIdleTimeout`, `GetSessionIdleTime`, and a callback for the headset's
activity level, so it may wait for input idle time that the VR session never reports.

## Waking from it

Once so far, a Frame the tweak put to sleep didn't wake normally. It slept on Nov 18 at 22:37
("PM: suspend entry (deep)", plugged in, battery full) and logged nothing more. On Nov 21 a first
short press of the power button did nothing visible; a second showed the boot logo and the Frame
started afresh, with the kernel reporting a warm reset (`PON: warm_reset_reason [0x02]: RESIN_N`)
and nothing logged in between. Sleeps started with the power button had resumed after 16 to 53
hours. One difference: Steam's own sleep logs "Issuing Suspend Command" before "Suspending", and
the tweak's `systemctl suspend` skips that step (Steam still logs "Suspending" and "Suspend
notification: entering"). Whether that matters, or the length of the sleep does, isn't known yet.

## What the tweak does

Reads the headset's last standby line in `vrserver.txt` every 30 seconds, and after 15 minutes of
standby on battery (60 plugged in, both adjustable) runs `systemctl suspend`, which logind allows
for the user's own services on SteamOS (polkit `org.freedesktop.login1.suspend`; checked with
`pkcheck` against a user service's process). Steam then logs "Suspend notification: entering" as for
any sleep. It holds off while someone is logged in over SSH (unless allowed), while a program
holds a *block* on sleep, and while SteamVR isn't running.

## Related

- Charging that stops while plugged in, so a Frame on its charger runs down: SteamOS #2879, and
  [battery-charge-limit.md](battery-charge-limit.md).
- A charger that loses its wall power looks to the headset like an unplug: cutting the power with
  the cable still in dropped the USB-C partner (`/sys/class/typec/port0-partner`) as pulling the
  cable did, so nothing on the headset can tell the two apart.
