# Screen reader

Turns on KDE's screen reader for desktop mode. It uses **Orca**, which SteamOS already
includes, to read windows, menus and text aloud.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (a setting in your home folder)
> - **Changes:** One setting in `~/.config/kaccessrc` (its previous value is restored on removal)
> - **Unusual access:** Reads what's on screen (accessibility interface) and speaks it
> - **Undo:** `./install.sh uninstall screen-reader` (restores the previous setting)
<!-- /generated:glance -->

```sh
./install.sh screen-reader
```

- **Meta+Alt+S** turns it on or off at any time.
- Settings (voice, speed, verbosity): **System Settings → Accessibility → Screen Reader**, or
  `orca --setup`.
- It starts with desktop mode, so after installing, it begins the next time you open desktop
  mode (or press Meta+Alt+S now).

Removing the tweak puts KDE's screen-reader setting back to what it was before.

## Credits
[Orca](https://gitlab.gnome.org/GNOME/orca) (LGPL-2.1) by GNOME, started by KDE's `kaccess`.
The idea of switching it on for a SteamOS session came from [Jovian-NixOS](https://github.com/Jovian-Experiments/Jovian-NixOS).
See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status screen-reader` · Remove: `./install.sh uninstall screen-reader`
