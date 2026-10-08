# Curved world windows

When you **float a window in the world** (detach it from the dashboard), SteamVR shows it
flat, and there's no setting to change that: the curvature rule is hard-coded (curved in the
dashboard, theater per setting, flat in the world). This tweak presses **Toggle Curvature**
for you on every window you float, so they start curved like the dashboard.

It stays your choice: toggle a window flat and it stays flat. Moving it back into the
dashboard and out again curves it again (SteamVR resets the toggle when a window is
re-docked).

```sh
./install.sh curvature
```

**Restart SteamVR once after installing** (reboot is easiest). SteamVR opens the local port
the patch needs only when it starts; `./install.sh status curvature` says when it's waiting.

## How it works
- SteamVR's dashboard is a web page (`systemui`) in its own web helper. With the setting
  `VRWebHelper/DebuggerEnabled` it opens Chrome DevTools on `127.0.0.1:8087`.
- `sft-vr-debugger.service` turns that setting on **just before each SteamVR start**, and a
  `steamvr.service` drop-in puts it back as it was **when SteamVR stops** (SteamVR rewrites
  its settings file from memory, so it can only be changed while stopped). A value you set to
  `true` yourself is left alone.
- `sft-curvature.service` runs while SteamVR does and injects [`patch.js`](patch.js) (re-checked
  every 5 s, so it survives a dashboard reload). The patch checks windows a few times a second;
  for a world-docked window with no curvature choice yet, it calls the stock
  `ToggleCurvature()`. Nothing else in the dashboard is changed.
- Files: `~/.local/share/frame-tweaks/curvature/`, `~/.config/systemd/user/sft-*.service`,
  `~/.config/systemd/user/steamvr.service.d/sft-curvature.conf`. Home folder only.

**Security:** the DevTools port listens on `127.0.0.1` only, while SteamVR runs. Any program
running as your user could use it to change the dashboard, which such a program could do
anyway. SteamOS's **Developer Mode** may forward it to your network; keep Developer Mode off
unless you need it.

**With steam-frame-nix:** if you use its dashboard patches, its
[window curvature](https://github.com/lhns/steam-frame-nix/blob/main/docs/window-curvature.md)
module (adjustable curvature per window) works alongside this; both use the same port.

## Credits
The approach (SteamVR's dashboard DevTools port, set only while SteamVR runs, and how the
dashboard's `curvature` component works) is from
[lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s window-curvature and
steamvr-debugger modules (Apache-2.0). No code copied: theirs makes curvature adjustable
but still starts world windows flat. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status curvature` · Remove: `./install.sh uninstall curvature`
