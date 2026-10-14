---
title: VR dashboard patching (helper)
emoji: 🧩
category: VR windows
tier: helper
summary: >-
  Lets the VR windows tweaks adjust SteamVR's dashboard; installed automatically when needed
what: >-
  Lets the VR windows tweaks (Curved world windows, Back to the previous window, Pick up when
  floating, Scroll strips) and Android Mirror adjust SteamVR's dashboard. Installed
  automatically.
why: >-
  SteamVR's dashboard is a web page with no settings for these behaviours; each VR windows tweak
  is a small patch this injects while SteamVR runs.
author: Frame Tweaks
experimental: >-
  The base the VR windows tweaks share. They rely on SteamVR's internal dashboard code, which
  Valve can change in any update: each patch is checked when SteamVR starts and switched off if
  its code changed (shown in its status) until a Frame Tweaks update catches up.
icon: {theme: applications-system}
changes: >-
  `~/.local/share/frame-tweaks/vr-dashboard`, user units `sft-vr-debugger`, `sft-dashboard`, a
  `steamvr.service` drop-in
access: >-
  **Turns on SteamVR's dashboard DevTools port (`127.0.0.1:8087`) while SteamVR runs** and
  injects the installed patches into the dashboard. The port has no password: **any program on
  the Frame (sandboxed Flatpak apps included) can connect while SteamVR runs**, run code in the
  dashboard, and use what the patches can do (arrow keys through ydotool, taps on a mirrored
  phone, saving patch settings). It's only on while this helper is installed
survives_updates: >-
  Yes; after a SteamVR update it checks SteamVR's dashboard code and switches off each patch
  whose code changed
undo: "`./install.sh uninstall vr-dashboard` (after the VR windows tweaks)"
test: {offline: true}
---
# VR dashboard patching (helper)

The shared part of the **VR windows** tweaks ([Curved world windows](../curvature/),
[Back to the previous window](../float-return/), [Pick up when floating](../float-grab/), [Scroll strips](../scroll-strips/)). Installed automatically with them; each of
those tweaks is one small patch, which you switch on or off by ticking it in the installer window.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches off each patch whose code changed
> - **Changes:** `~/.local/share/frame-tweaks/vr-dashboard`, user units `sft-vr-debugger`, `sft-dashboard`, a `steamvr.service` drop-in
> - **🧪 Experimental:** The base the VR windows tweaks share. They rely on SteamVR's internal dashboard code, which Valve can change in any update: each patch is checked when SteamVR starts and switched off if its code changed (shown in its status) until a Frame Tweaks update catches up.
> - **Unusual access:** **Turns on SteamVR's dashboard DevTools port (`127.0.0.1:8087`) while SteamVR runs** and injects the installed patches into the dashboard. The port has no password: **any program on the Frame (sandboxed Flatpak apps included) can connect while SteamVR runs**, run code in the dashboard, and use what the patches can do (arrow keys through ydotool, taps on a mirrored phone, saving patch settings). It's only on while this helper is installed
> - **Undo:** `./install.sh uninstall vr-dashboard` (after the VR windows tweaks)
<!-- /generated:glance -->

**Restart SteamVR once after installing** (reboot is easiest). SteamVR opens the local port
the patches need only when it starts; `./install.sh status vr-dashboard` says when it's waiting.

## How it works
- SteamVR's dashboard is a web page (`systemui`) in its own web helper. With the setting
  `VRWebHelper/DebuggerEnabled` it opens Chrome DevTools on `127.0.0.1:8087`.
- `sft-vr-debugger.service` turns that setting on **just before each SteamVR start**, and a
  `steamvr.service` drop-in puts it back as it was **when SteamVR stops** (SteamVR rewrites
  its settings file from memory, so it can only be changed while stopped). A value you set to
  `true` yourself is left alone.
- `sft-dashboard.service` runs while SteamVR does and injects every patch in
  `~/.local/share/frame-tweaks/vr-dashboard/patches/` (re-checked every 5 s, so it survives a
  dashboard reload). A patch whose file is removed (its tweak unticked) is stopped in the
  running dashboard.
- Each patch lists the pieces of SteamVR's dashboard code it relies on (`// requires:` lines).
  After a SteamVR update that changed any of them, that patch isn't injected and its status says
  so, instead of poking at code it doesn't understand. `sft-dashboard check` shows the result.
- Files: `~/.local/share/frame-tweaks/vr-dashboard/`, `~/.config/systemd/user/sft-*.service`,
  `~/.config/systemd/user/steamvr.service.d/sft-dashboard.conf`. Home folder only.
- Before this helper existed, Curved world windows did all this itself (`sft-curvature`); the
  first install of this helper moves that setup over.

## Credits
The approach (SteamVR's dashboard DevTools port, patching the dashboard page) follows
[lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix/blob/main/docs/window-curvature.md).
See also [CREDITS.md](../../../CREDITS.md).
