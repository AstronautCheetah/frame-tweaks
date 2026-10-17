---
title: VR dashboard patching (helper)
emoji: 🧩
category: VR environment
tier: helper
summary: >-
  Lets the VR environment tweaks adjust SteamVR's dashboard; installed automatically when needed
what: >-
  The shared part of the VR environment tweaks (Curved world windows, Back to the previous window,
  Pick up when floating, Scroll strips): it puts their small patches into SteamVR's dashboard
  while SteamVR runs. Android Mirror uses it too when it's there. Installed automatically. Its own
  patches help Frame Tweaks' panels in VR (Arrow Pad, Screen snip's narration panel) with Steam's
  keyboard: pressing one leaves the keyboard with the window you're typing in, and while it's
  open, SteamVR's grab bar under each panel moves it anywhere.
why: >-
  SteamVR's dashboard, the menu and window space you use in the headset, has no settings for
  these behaviours. It's a web page, so small patches added to it while SteamVR runs can change
  them.
author: Frame Tweaks
experimental: >-
  The base the VR environment tweaks share. They rely on SteamVR's internal dashboard code, which
  Valve can change in any update: each time SteamVR starts, every patch is checked against that
  code and left out if a piece it needs is gone (shown in its status) until a Frame Tweaks update
  catches up.
icon: {theme: applications-system}
changes: >-
  `~/.local/share/frame-tweaks/vr-dashboard`, user units `sft-vr-debugger`, `sft-dashboard`, a
  `steamvr.service` drop-in; SteamVR's `VRWebHelper/DebuggerEnabled` setting while SteamVR runs.
  Reads where Frame Tweaks' VR panels are (and their pictures) from
  `$XDG_RUNTIME_DIR/frame-tweaks/panels`, and writes there where one was moved
access: >-
  **Turns on SteamVR's dashboard DevTools port (`127.0.0.1:8087`) while SteamVR runs** and
  injects the installed patches into the dashboard. The port has no password: **any program on
  the Frame that can reach the local network (Flatpak apps with network access included) can
  connect while SteamVR runs**, run code in the dashboard, and use what the patches can do (arrow
  keys through ydotool, taps on a mirrored phone, saving patch settings, moving Frame Tweaks'
  panels). It's only on while this helper is installed
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and leaves out each patch that
  no longer fits it
undo: "`./install.sh uninstall vr-dashboard` (after the VR environment tweaks)"
test: {offline: true}
---
# VR dashboard patching (helper)

<!-- generated:intro (dev/gen-docs.py, from each tweak's README front matter) -->
The shared part of the VR environment tweaks (Curved world windows, Back to the previous window, Pick up when floating, Scroll strips): it puts their small patches into SteamVR's dashboard while SteamVR runs. Android Mirror uses it too when it's there. Installed automatically. Its own patches help Frame Tweaks' panels in VR (Arrow Pad, Screen snip's narration panel) with Steam's keyboard: pressing one leaves the keyboard with the window you're typing in, and while it's open, SteamVR's grab bar under each panel moves it anywhere.

**Why on a Steam Frame:** SteamVR's dashboard, the menu and window space you use in the headset, has no settings for these behaviours. It's a web page, so small patches added to it while SteamVR runs can change them.
<!-- /generated:intro -->

## Install
You don't need to tick it yourself: it's installed with the first of
[Curved world windows](../curvature/), [Back to the previous window](../float-return/),
[Pick up when floating](../float-grab/) or [Scroll strips](../scroll-strips/) you install. By
hand:

```sh
./install.sh install vr-dashboard
```

**If SteamVR was running, restart it once** (rebooting is easiest). SteamVR opens the local
port the patches need only when it starts. `./install.sh status vr-dashboard` says when it's
waiting for that.

## Use
Nothing to do here. Each VR environment tweak is one patch; tick or untick those tweaks in the
Frame Tweaks window, and the running dashboard picks up the change within a few seconds.

One patch is its own, `panel-keyboard`. Steam's keyboard follows the laser: pressing a Frame
Tweaks panel ([Arrow Pad](../arrowpad/), [Screen snip](../snip/)'s narration panel) while you type
took the keyboard away from your window (what you typed next went nowhere) and moved it. The
patch gives it straight back to the window it was open for, where it was.

Another is `panel-grab`. While Steam's keyboard is open, SteamVR hides where your controllers are
from every other program (so an app can't tell what you type from how your hands move), and
Frame Tweaks' panels can only slide after the laser. SteamVR's own dashboard can still move
things: this patch puts the grab bar it draws under desktop windows under each panel, for as
long as the keyboard is open. Hold it with the trigger and a picture of the panel follows your
hand (the thumbstick pushes it away or pulls it closer); let go, and the panel takes its place.
The panel is told only where you let go, never where your controller is. They say where they
are, and get told where they went, through small files in `$XDG_RUNTIME_DIR/frame-tweaks/panels`
that the service relays.

## How it works
- SteamVR's dashboard is a web page (`systemui`) in its own web helper. With the setting
  `VRWebHelper/DebuggerEnabled` it opens Chrome DevTools on `127.0.0.1:8087`.
- `sft-vr-debugger.service` turns that setting on **just before each SteamVR start**, and a
  `steamvr.service` drop-in puts it back as it was **when SteamVR stops** (SteamVR rewrites
  its settings file from memory, so it can only be changed while stopped). If you had already
  set it to `true` yourself, it's left alone.
- `sft-dashboard.service` runs while SteamVR does and injects every patch in
  `~/.local/share/frame-tweaks/vr-dashboard/patches/`. It looks again every 5 seconds, so the
  patches come back after a dashboard reload, and a patch whose file is removed (its tweak
  unticked) is stopped in the running dashboard.
- Each patch lists the pieces of SteamVR's dashboard code it relies on (`// requires:` lines in
  the patch). When the service starts with SteamVR, it looks for each of those pieces in the
  dashboard's files. A patch with a piece missing isn't injected, and its status says which
  piece. If a piece the shared helper code (`lib.js`) needs is missing, every patch stays off.
  `~/.local/share/frame-tweaks/vr-dashboard/sft-dashboard check` shows the result.
- Patches that need something the page can't do itself ask the service: Scroll strips sends
  arrow keys through [ydotool](../ydotool/), and settings changed from a panel in VR are saved
  to `~/.config/frame-tweaks/NAME.json` (only for an installed patch).
- Files: `~/.local/share/frame-tweaks/vr-dashboard/`, `~/.config/systemd/user/sft-*.service`,
  `~/.config/systemd/user/steamvr.service.d/sft-dashboard.conf`. Home folder only.

## Good to know
- Uninstalling while SteamVR runs stops the patches at once; the DevTools setting goes back as
  it was when SteamVR next stops.

<!-- generated:changes (dev/gen-docs.py, from each tweak's README front matter) -->
## What it changes

- **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and leaves out each patch that no longer fits it
- **Changes:** `~/.local/share/frame-tweaks/vr-dashboard`, user units `sft-vr-debugger`, `sft-dashboard`, a `steamvr.service` drop-in; SteamVR's `VRWebHelper/DebuggerEnabled` setting while SteamVR runs. Reads where Frame Tweaks' VR panels are (and their pictures) from `$XDG_RUNTIME_DIR/frame-tweaks/panels`, and writes there where one was moved
- **🧪 Experimental:** The base the VR environment tweaks share. They rely on SteamVR's internal dashboard code, which Valve can change in any update: each time SteamVR starts, every patch is checked against that code and left out if a piece it needs is gone (shown in its status) until a Frame Tweaks update catches up.
- **Unusual access:** **Turns on SteamVR's dashboard DevTools port (`127.0.0.1:8087`) while SteamVR runs** and injects the installed patches into the dashboard. The port has no password: **any program on the Frame that can reach the local network (Flatpak apps with network access included) can connect while SteamVR runs**, run code in the dashboard, and use what the patches can do (arrow keys through ydotool, taps on a mirrored phone, saving patch settings, moving Frame Tweaks' panels). It's only on while this helper is installed
- **Undo:** `./install.sh uninstall vr-dashboard` (after the VR environment tweaks)
<!-- /generated:changes -->

## Credits
The approach (SteamVR's dashboard DevTools port, patching the dashboard page) follows
[lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix/blob/main/docs/window-curvature.md).
See also [CREDITS.md](../../../CREDITS.md).

---
Check: `./install.sh status vr-dashboard` · Remove: `./install.sh uninstall vr-dashboard`
