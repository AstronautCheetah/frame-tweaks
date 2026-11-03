---
title: KnockThru
emoji: ✊
category: VR environment
tier: extras
summary: Knock twice on your headset or a table to turn passthrough on or off
what: >-
  VioletTides' KnockThru: knock the controllers together, one controller on a table (or your leg), or on the
  headset, and passthrough (Room View) turns on or off. A double knock toggles it, a triple knock can switch its style; you
  pick and calibrate your knocks in its tab in the SteamVR dashboard. It starts with SteamVR.
why: >-
  Checking the room means finding the Room View button in the dashboard, or a controller
  binding. A knock works with a controller in your hand or set down. Linked: it installs the
  release Frame Tweaks tested with its own installer, the way its README describes.
author: VioletTides (KnockThru)
source:
  relation: from
  url: https://github.com/VioletTides/KnockThru
experimental: >-
  KnockThru presses Room View through Steam's own dashboard, over CEF Remote Debugging, which you
  turn on in the Developer settings: a Steam update that moves the button stops it until
  KnockThru catches up (three buzzes after a knock, and its tab says why). While CEF Remote
  Debugging is on, programs on the headset can control Steam's interface; turn it off when you
  stop using KnockThru.
icon: {theme: view-visible}
processes: [/KnockThru/knockthru( |$)]
config: [~/.config/knockthru]
link:
  install: d=$(mktemp -d) && trap 'rm -rf "$d"' EXIT && u=https://github.com/VioletTides/KnockThru/releases && if [ -n "$FT_LINK_VERSION" ]; then u=$u/download/$FT_LINK_VERSION; else u=$u/latest/download; fi && curl -fsSL "$u/install.sh" -o "$d/install.sh" && KNOCKTHRU_RELEASE_URL=$u sh "$d/install.sh"
  uninstall: ~/KnockThru/knockthru --uninstall && rm -rf ~/KnockThru
  installed: ~/KnockThru/knockthru
  version: python3 -c 'import json, os; print(json.load(open(os.path.expanduser("~/.config/knockthru/state.json")))["knockthru_version"])'
  readme: https://github.com/VioletTides/KnockThru#readme
changes: >-
  Whatever KnockThru's own installer sets up (its README lists it): the program in
  `~/KnockThru`, registered with SteamVR to start with it, and a Non-Steam entry in your Steam
  library
access: >-
  Reads controller and headset motion from SteamVR; presses Room View through Steam's interface
  (CEF Remote Debugging, which you turn on); asks GitHub once a day for a newer release
survives_updates: Yes (everything is in your home folder); a Steam update can move the button it presses
undo: >-
  Uncheck it, or `./install.sh uninstall knockthru`: KnockThru's own `--uninstall`, then its
  folder is deleted (keeps its settings and calibration in `~/.config/knockthru`). Remove its
  Non-Steam library entry and turn CEF Remote Debugging off yourself.
---
# KnockThru

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
VioletTides' KnockThru: knock the controllers together, one controller on a table (or your leg), or on the headset, and passthrough (Room View) turns on or off. A double knock toggles it, a triple knock can switch its style; you pick and calibrate your knocks in its tab in the SteamVR dashboard. It starts with SteamVR.

**Why on a Steam Frame:** Checking the room means finding the Room View button in the dashboard, or a controller binding. A knock works with a controller in your hand or set down. Linked: it installs the release Frame Tweaks tested with its own installer, the way its README describes.
<!-- /generated:intro -->

A **link**: Frame Tweaks runs KnockThru's own steps, as its
[README](https://github.com/VioletTides/KnockThru#readme) gives them, in the terminal it opens
for installs, and doesn't change what they install.

**Before you install:** turn on **Developer Mode**, then **CEF Remote Debugging** in the
Developer settings. KnockThru needs it to press Room View for you. Leaving it on lets programs
on the headset control Steam's interface, not just KnockThru: turn it off again if you remove
KnockThru.

- **Install** (tick it): downloads the installer from the KnockThru release Frame Tweaks tested
  (`link-knockthru` in `lib/tested-versions`) and runs it with that release
  (`KNOCKTHRU_RELEASE_URL`). The installer downloads it, checks its SHA-256, unpacks it to `~/KnockThru`,
  adds it to your Steam library under Non-Steam, and starts it. If SteamVR doesn't answer,
  launch **KnockThru** once from **Library → Non-Steam** in Gaming mode.
- **Update:** when VioletTides publishes a release newer than the one Frame Tweaks tested, its row
  offers it as *not yet tested by Frame Tweaks* (↑ *version* available · **Update**); once
  it's installed, **↩ Back to the tested version** installs the tested one again. Frame
  Tweaks' own updates move it to a newer tested version, never to an untested one.
  `./install.sh link-version knockthru tested|newest` does the same.
  Its own **Check for updates** in its Settings installs its newest too.
- **Uninstall** (untick it): runs `~/KnockThru/knockthru --uninstall`, which stops it and
  removes it from SteamVR, then deletes `~/KnockThru`. Your settings and calibration in
  `~/.config/knockthru` stay; `~/KnockThru/knockthru --uninstall --purge` before unticking
  removes them too. The Non-Steam entry in your library stays: remove it there.

## Use

The first time you open its **KnockThru** tab in the SteamVR dashboard, a short tour helps you
pick your knocks, calibrate them and try them. The **KnockThru On** switch at the top pauses
knocking. Its [README](https://github.com/VioletTides/KnockThru#readme) covers the knocks, the
settings and the troubleshooting.

- **Three buzzes after a knock:** it heard you but couldn't change passthrough. Usually CEF
  Remote Debugging is off, or a Steam update moved the Room View button; its tab says which.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes (everything is in your home folder); a Steam update can move the button it presses
- **Changes:** Whatever KnockThru's own installer sets up (its README lists it): the program in `~/KnockThru`, registered with SteamVR to start with it, and a Non-Steam entry in your Steam library
- **🧪 Experimental:** KnockThru presses Room View through Steam's own dashboard, over CEF Remote Debugging, which you turn on in the Developer settings: a Steam update that moves the button stops it until KnockThru catches up (three buzzes after a knock, and its tab says why). While CEF Remote Debugging is on, programs on the headset can control Steam's interface; turn it off when you stop using KnockThru.
- **Unusual access:** Reads controller and headset motion from SteamVR; presses Room View through Steam's interface (CEF Remote Debugging, which you turn on); asks GitHub once a day for a newer release
- **Undo:** Uncheck it, or `./install.sh uninstall knockthru`: KnockThru's own `--uninstall`, then its folder is deleted (keeps its settings and calibration in `~/.config/knockthru`). Remove its Non-Steam library entry and turn CEF Remote Debugging off yourself.
<!-- /generated:changes -->

## Credits

KnockThru is by [VioletTides](https://github.com/VioletTides/KnockThru) (MIT); its controller and
headset drawings come from Valve's Steam Frame CAD files (CC BY-NC-SA 4.0). Frame Tweaks only
runs its install steps. See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status knockthru` · Remove: `./install.sh uninstall knockthru`
