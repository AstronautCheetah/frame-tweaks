# Arrow Pad

A compact, always-on-top pad for desktop mode with the keys Steam's on-screen
keyboard lacks. It never steals focus, so whatever you tap goes to the app you're
working in.

```
 nav layer                              Fn layer
 Esc   Tab   Bksp  Del   Enter  Fn      F1   F2   F3   F4    F5    Fn
 Shift Home   ↑    End   PgUp   🎤      F6   F7   F8   F9    F10   🎤
 Ctrl   ←     ↓     →    PgDn   Copy    F11  F12  Ins  PrtSc Menu  Copy
 Alt   Super Undo  Cut   All    Paste   Alt  Super Undo Cut   All   Paste
```

Two menu entries, usable from the desktop menu *or* Steam's VR "+" menu:
- **Arrow Pad** (`arrowpad --desktop`): inside desktop mode.
- **Arrow Pad (VR window)** (`arrowpad --vr`): a **native SteamVR overlay**, like Full
  Keyboard. Visible while the dashboard is; point and pull the trigger to type. It sits **just
  below Steam's dashboard** (its main panel, or the dashboard bar when that's what's showing),
  tilted back 50°, and **follows the dashboard** when it moves or the play space is re-centred,
  using Full Keyboard's placement. **Reset** puts it back there, **−/+** change its width in 5 cm steps (0.30–2 m), point at the panel's
  background and hold the trigger to carry it with your controller (like Full Keyboard's grab),
  **Pin** stops that. Launching it again (menu or ▶ Open) recenters it in front of you. It never takes keyboard focus, so keys reach the app you were using; a
  floating *window* couldn't do that (gamescope gives clicked windows focus and ignores requests
  to hand it back).

They're separate instances, so you can have both. Each remembers its own position.

```sh
./install.sh arrowpad
arrowpad --desktop       # launch; run again to hide/show it (bind this to a shortcut)
arrowpad --scale 1.5     # bigger buttons (or ARROWPAD_SCALE=1.5)
arrowpad --quit
```

**Looks and handles like Full Keyboard:** its Graphite theme (dark panel, gradient keycaps,
latched-blue modifiers) and a toolbar with 📌 **pin** (stops accidental moves), ⌖ **reset
position** (bottom centre), **−** / **+** (size, 0.6×–2×) and ✕ close. **Grab to move:** drag
the panel or toolbar background. Position, size and pin state are remembered per window.

**Controller haptics, like Full Keyboard:** a light tick when the laser moves onto a key and a
click when you press one, on the controller that's pointing (the overlay events say which).
Full Keyboard's values; the toolbar and dragging don't pulse. SteamVR only delivers haptics to
the app with input focus, which an overlay has while you point at it; the desktop pad, an
ordinary window, may not get them.

**Sizing:** the pad keeps its proportions. In desktop mode **+**/**−** change the key size
(0.6×–2×); in VR they change the overlay's physical width (5 cm steps), like Full Keyboard.

**Labels follow your keyboard language:** the pad reads KDE's current layout (re-checked every
few seconds) and uses the legends printed on that language's keyboards: German *Strg, Entf,
Einfg, Pos1, Bild↑*, French *Échap, Suppr, Début*, Spanish *Supr, Inicio, RePág*, Italian
*Canc, Inizio, Pag↑*; English otherwise. Copy, paste, cut, undo and select-all are icons.

- **Modifiers** (Shift, Ctrl, Alt, Super): tap = one-shot (applies to the next key,
  then releases), **double-tap = lock** (outlined) until tapped again. A held modifier
  also applies to mouse clicks (Ctrl+click, Shift+click).
- **Hold to repeat**: holding a button holds the key, so the app's key repeat applies.
- **Fn** switches to F1–F12, Insert, PrintScreen and Menu.
- **Copy / Paste / Cut / Undo / Select all** (icons) send the Ctrl shortcuts.
- **🎤** toggles [dictation](../dictation/): red while recording, yellow while transcribing. The text
  goes to the focused app, because the pad never takes focus.
- **Toggle, don't duplicate**: launching again hides/shows the running pad. The
  position is remembered in `~/.config/arrowpad.json`.

## Which keyboard when?

| Situation | Best tool |
|---|---|
| Typing text in VR, dashboard or floating app windows | [Full Keyboard](../full-keyboard/) (laser typing, full layout) |
| Quick text entry anywhere | Steam keyboard (Steam + X). Hold **Shift** for ←/→ |
| Navigating / editing in desktop-mode apps (arrows, selection, shortcuts, F-keys) | **Arrow Pad** |
| Lots of text | [Dictation](../dictation/) (🎤 on the pad, or its shortcut) |
| Nix user who wants arrows/Esc/Ctrl inside Steam's own VR keyboard, plus swipe | [steam-frame-nix VR keyboard](https://github.com/lhns/steam-frame-nix/blob/main/docs/keyboard.md) |

## Ideas borrowed
- Look, toolbar, pin, recenter and size buttons: from [Full Keyboard](https://github.com/TaiKeid/steam-frame-full-keyboard)
  (its Graphite theme colours, MIT). Toolbar and clipboard icons: KDE Breeze.
- One-shot / double-tap-lock modifiers and the F-key layer: from steam-frame-nix's VR
  keyboard patch and Full Keyboard.
- Copy/Paste buttons and "launch again recenters instead of duplicating": from Full Keyboard.

## How it works
- Runs under XWayland with the X11 "doesn't accept input focus" hint, which KWin
  honours. Native Wayland has no equivalent for ordinary windows.
- Sends real key down/up events by writing `struct input_event` datagrams straight to
  `ydotoold`'s socket (no subprocess per key).
- Single instance via a `QLocalServer` socket (`arrowpad-$UID`).
- PyQt6 in a private venv (`~/.local/share/arrowpad/venv`, ~280 MB), because SteamOS
  ships no Python GUI bindings.

## Credits
Look, toolbar, pin/recenter/size controls and haptic values from [TaiKeid/steam-frame-full-keyboard](https://github.com/TaiKeid/steam-frame-full-keyboard) (MIT); one-shot modifiers and the F-key layer from [lhns/steam-frame-nix](https://github.com/lhns/steam-frame-nix)'s VR keyboard (Apache-2.0). Icons: KDE Breeze (LGPL-3.0). Haptics via [pyopenvr](https://github.com/cmbruns/pyopenvr) (BSD). See also [CREDITS.md](../CREDITS.md).

---
Check: `./install.sh status arrowpad` · Remove: `./install.sh uninstall arrowpad`
