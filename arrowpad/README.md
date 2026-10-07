# Arrow Pad

The Steam on-screen keyboard has no up/down keys (hold **Shift** on it to get ←/→).
Arrow Pad is a small floating, always-on-top pad that fills the gap:

```
Esc   Tab   Bksp  Del   Enter
Shift Home   ↑    End   PgUp
Ctrl   ←     ↓     →    PgDn
```

```sh
./install.sh arrowpad
arrowpad --scale 1.5      # bigger buttons (or ARROWPAD_SCALE=1.5)
```

- Tapping it **never steals focus**, so keys go to the app you're working in.
- Holding a button holds the key, so the app's normal key repeat applies.
- Shift / Ctrl are sticky toggles (e.g. Shift on + arrows = select text).

## How it works
- Runs under XWayland with the X11 "doesn't accept input focus" hint, which KWin
  honours. Native Wayland has no equivalent for ordinary windows.
- Sends real key down/up events by writing `struct input_event` datagrams straight
  to `ydotoold`'s socket (no subprocess per key).
- PyQt6 in a private venv (`~/.local/share/arrowpad/venv`, ~280 MB), because SteamOS
  ships no Python GUI bindings.
