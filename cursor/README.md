# Mouse cursor fix

In desktop mode the mouse moves, but its pointer isn't drawn: KWin puts the cursor
on a hardware plane that the headset's view doesn't show. `KWIN_FORCE_SW_CURSOR=1`
makes KWin draw it into the frame itself.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `~/.config/environment.d/` (one variable for KWin)
> - **Undo:** `./install.sh uninstall cursor`
<!-- /generated:glance -->

```sh
./install.sh install cursor     # then reboot
env | grep KWIN         # in a desktop-mode terminal: KWIN_FORCE_SW_CURSOR=1
```

Undo: delete `~/.config/environment.d/90-kwin-software-cursor.conf` and reboot.

Credit: from [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils),
via Cas and Chary XR's "Steam Frame: 10 Things To Do FIRST", credited there to ThrillSeeker.

## Credits
From [curiousjtuber/steam-frame-utils](https://github.com/curiousjtuber/steam-frame-utils), via Cas and Chary XR's "Steam Frame: 10 Things To Do FIRST", credited there to ThrillSeeker. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status cursor` · Remove: `./install.sh uninstall cursor`
