# ydotool (shared helper)

Keystroke injection via the kernel's uinput: the only way for ordinary programs to type
into any app under KDE Wayland. Installed automatically by `dictation` and `arrowpad`.

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `ydotool`/`ydotoold` (Arch Linux ARM, signature-checked), user service `ydotoold`
> - **Unusual access:** **Writes to `/dev/uinput`** (a virtual keyboard any program you run could use while it's running)
> - **Undo:** `./install.sh uninstall ydotool`
<!-- /generated:glance -->

## What uses it

Nothing you open yourself: it's the "virtual keyboard" other tweaks type through.

| Tweak | How it uses ydotool |
|---|---|
| [Dictation](../dictation/) | After Whisper turns your speech into text, `ydotool type` types it into the focused window, letter by letter (`--key-delay 2`), as if you'd typed it. The text is also copied, so you can paste it if typing is turned off (`DICTATE_NOTYPE=1`). |
| [Arrow Pad](../arrowpad/) (desktop and VR) | Each button sends real key-down/key-up events (arrows, Esc, Home/End, F-keys, Ctrl+C/V for Copy/Paste, …) straight to `ydotoold`'s socket. Holding a button holds the key, so key repeat works; modifiers stay down across the next key, so Ctrl+Shift+→ works. The pad never takes focus, so the keys land in the app you were using. |
| Arrow Pad's 🎤 | Starts and stops Dictation, which then types through ydotool as above. |

Why not something simpler: under KDE Wayland ordinary programs can't send keystrokes to other
apps (`xdotool` only reaches X11 windows). ydotool writes to the kernel's `/dev/uinput`, so
apps see a real keyboard. **▶ Restart** restarts `ydotoold` if typing stops working (for
example after resuming from sleep).

## Details

- `ydotool` / `ydotoold` binaries from Arch Linux ARM → `~/.local/bin`
- user service `ydotoold.service`, socket `/run/user/$UID/.ydotool_socket`
- requires write access to `/dev/uinput` (the `input` group, which SteamOS grants by default)

## Credits
[ydotool](https://github.com/ReimuNotMoe/ydotool) (AGPL-3.0) by ReimuNotMoe, from [Arch Linux ARM](https://archlinuxarm.org)'s package, not modified. See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status ydotool` · Remove: `./install.sh uninstall ydotool`
