# Dictate and Lock Wallet on a controller button

Two steps: give each action a **keyboard shortcut** in the desktop, then have **Steam Input**
press that shortcut when you press a controller button. Steam keeps controller layouts in its
own settings, so this is done in Steam's UI, not by a script.

## 1. Keyboard shortcuts (desktop mode)

In the desktop (System Settings is in the "+" menu):

1. **System Settings → Keyboard → Shortcuts → Add New → Application…**
2. Pick **Dictate (toggle)**, then click its entry and press the shortcut. Suggested:
   **Meta+Alt+D**.
3. **Add New → Application…** again, pick **Lock Wallet**, suggested **Meta+Alt+L**.
   (Meta+L already locks the screen.)
4. **Apply.** Test them with a keyboard if you have one (the Arrow Pad has no letter keys).

## 2. A controller button that presses the shortcut (Steam Input)

1. In Steam: **Settings → Controller → Desktop Layout → Edit**.
2. Choose a button you don't use in the desktop. Good candidates: a **long press** or a
   **chord** (hold one button, press another) so you can't trigger it by accident.
3. Set its command to **Keyboard Key** with modifiers: Meta (Super/Windows), Alt and **D**
   for Dictate; the same with **L** for Lock Wallet. In Steam's binding editor that's "Add
   extra command" for each key of the combination, or "Key chord", depending on the version.
4. Save the layout.

**Does it reach the VR desktop?** Steam applies the *Desktop Layout* when no game is running.
Inside SteamVR the controllers mainly act as laser pointers, and Steam may not apply the
desktop layout there; that depends on the SteamOS build and isn't documented. If the button
does nothing in VR:

- **Dictate:** use **Tools → 🎤** on the [Arrow Pad](../packs/original/arrowpad/) (desktop or VR),
  or the ▶ Dictate button in Frame Tweaks.
- **Lock Wallet:** the **Lock Wallet** entry in the "+" menu or the desktop menu, or
  `wallet-unlock --lock` in a terminal. The wallet also locks itself after a set time (4 hours unless you change it on the
  Wallet apps page).

## Undo

Remove the shortcuts in System Settings → Keyboard → Shortcuts, and the bindings in Steam's
Desktop Layout editor (or "Reset to default").
