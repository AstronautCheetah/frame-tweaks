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

```sh
./install.sh arrowpad
arrowpad                 # launch; run again to hide/show it (bind this to a shortcut)
arrowpad --scale 1.5     # bigger buttons (or ARROWPAD_SCALE=1.5)
arrowpad --quit
```

- **Modifiers** (Shift, Ctrl, Alt, Super): tap = one-shot (applies to the next key,
  then releases), **double-tap = lock** (outlined) until tapped again. A held modifier
  also applies to mouse clicks (Ctrl+click, Shift+click).
- **Hold to repeat**: holding a button holds the key, so the app's key repeat applies.
- **Fn** switches to F1–F12, Insert, PrintScreen and Menu.
- **Copy / Paste / Cut / Undo / All** send the Ctrl shortcuts.
- **🎤** toggles [dictation](../dictation/) and turns red while recording. The text
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
