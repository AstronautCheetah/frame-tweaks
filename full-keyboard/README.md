# Full Keyboard (VR)

[TaiKeid/steam-frame-full-keyboard](https://github.com/TaiKeid/steam-frame-full-keyboard)
(MIT): a full-size VR keyboard for the Frame's dashboard and local apps, typed with
the controller lasers. It has arrows, F-keys, a numpad, Ctrl/Alt, Copy/Paste, haptics,
grab-to-move, and many languages. It's a separate app (the system keyboard button
still opens Steam's).

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** Upstream's own installer into `~/.local/share/framekeyboard`, pinned release
> - **Unusual access:** A SteamVR overlay; types through its own input path
> - **Undo:** `./install.sh uninstall full-keyboard` (keeps its settings in `~/.config/framekeyboard`)
<!-- /generated:glance -->

```sh
./install.sh install full-keyboard    # latest release, SHA256-verified, then its own installer
```

Launch **Full Keyboard** from the dashboard's app launcher. Launching again recenters it.
Re-run the install to update; the upstream installer keeps the previous release for rollback.

**Which keyboard when?** See the [keyboard guide](../arrowpad/README.md#which-keyboard-when).

## Credits
Full Keyboard is [TaiKeid](https://github.com/TaiKeid/steam-frame-full-keyboard)'s (MIT). The checksum-then-install pattern follows [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils)' `install-full-keyboard.sh`. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status full-keyboard` · Remove: `./install.sh uninstall full-keyboard`
