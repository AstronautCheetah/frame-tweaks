# Clipboard: one clipboard for desktop mode and VR windows

**Problem:** the Frame runs two sessions: Steam/VR (its floating windows live on X display
`:0`) and the nested Plasma desktop (its own Wayland and X `:2`). They have **separate
clipboards**, so copying in a floating VR window and pasting in the desktop (or back) doesn't
work.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `clipboard-sync` built from source, KDE autostart entry
> - **Unusual access:** Reads and writes both sessions' clipboards
> - **Undo:** `./install.sh uninstall clipboard`
<!-- /generated:glance -->

**Fix:** [dnut/clipboard-sync](https://github.com/dnut/clipboard-sync) watches every X11 and
Wayland clipboard it can reach and keeps them in sync. Started with the desktop session, it
sees both.

```sh
./install.sh clipboard
```

- Built from **upstream source** with Rust (Homebrew), so re-running the install picks up
  upstream changes. The first build takes a few minutes.
- Starts with desktop mode via KDE autostart (`~/.config/autostart/clipboard-sync.desktop`).
  It needs the desktop session's environment: started from VR or a user service, it wouldn't
  see the desktop's clipboard.

## Credits
This is the approach of [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s
`clipboardSync` module (Apache-2.0), done without Nix; the tool is
[dnut/clipboard-sync](https://github.com/dnut/clipboard-sync). See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status clipboard` · Remove: `./install.sh uninstall clipboard`
