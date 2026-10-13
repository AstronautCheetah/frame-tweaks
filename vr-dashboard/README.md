# VR dashboard patching (helper)

The shared part of the **VR windows** tweaks ([Curved world windows](../curvature/),
[Back to the previous window](../float-return/), [Pick up when floating](../float-grab/), [Scroll strips](../scroll-strips/)). Installed automatically with them; each of
those tweaks is one small patch, which you switch on or off by ticking it in the installer window.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes; after a SteamVR update it checks SteamVR's dashboard code and switches off each patch whose code changed
> - **Changes:** `~/.local/share/frame-tweaks/vr-dashboard`, user units `sft-vr-debugger`, `sft-dashboard`, a `steamvr.service` drop-in
> - **Unusual access:** **Turns on SteamVR's dashboard DevTools port (`127.0.0.1:8087`) while SteamVR runs** and injects the installed patches into the dashboard. Any program running as you could use that port too
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
See also [CREDITS.md](../CREDITS.md).
