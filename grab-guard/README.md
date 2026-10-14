# Grab guard: notice when desktop mode takes all input

**Problem:** desktop mode on the Frame is a nested KWin running as a window of the Steam session.
**A Right Ctrl press toggles its input grab.** While it's grabbed, every key and click goes to
the desktop: Frame Tweaks, floating windows and the rest stop responding, and nothing says why
except the desktop window's title ("Press right control to **ungrab** input").

<!-- generated:glance (dev/gen-docs.py, from each tweak's meta) -->
> **At a glance**
>
> - **Survives SteamOS updates:** Yes (everything is in your home folder)
> - **Changes:** `grab-guard`, user service `grab-guard`, a log in `~/.local/state/frame-tweaks/logs`
> - **Unusual access:** **Reads every keyboard's key presses**, and the Steam session's display's (only to notice Right Ctrl; nothing else is kept)
> - **Undo:** `./install.sh uninstall grab-guard`
<!-- /generated:glance -->

**Fix:** a small watcher (`grab-guard`, a user service) checks that title every second. When
the grab turns on it shows a notification: tap **Right Ctrl** on a keyboard once to release it.
It also logs where the Right Ctrl came from, so a stray source can be tracked down: which input
device sent it (a Bluetooth keyboard, the virtual keyboard that Arrow Pad and Dictation type
through, a controller…), and how the Steam session's display got it (also keys that never pass
through an input device: faked by an X program (XTest), or typed through libei, as Full
Keyboard does): `~/.local/state/frame-tweaks/logs/grab-guard.log`, or `grab-guard --status`.

```sh
./install.sh install grab-guard
```

It never sends a key itself: sending Right Ctrl is exactly what flips the grab, and Frame
Tweaks' own key clean-ups (Arrow Pad's Unstick, the stuck-key reset) leave it out for that
reason.

---
Check: `./install.sh status grab-guard` · Remove: `./install.sh uninstall grab-guard`
