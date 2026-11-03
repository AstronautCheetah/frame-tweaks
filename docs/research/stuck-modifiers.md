# Stuck modifiers: where a held Shift lives, and what can let go of it

For maintainers; not shown in the app. Why Arrow Pad's **Unstick** can release some stuck keys and
not others, found on a Frame on 3 November 2026 (SteamOS 0.5.6 beta) with a Bluetooth keyboard
whose Shift stayed "held" for every app until SteamVR was restarted. The short version is in
[Arrow Pad's README](../../packs/core/arrowpad/README.md) (*Unstick*).

## The layers a key press goes through

1. **The kernel**, per device. `EVIOCGKEY` says which keys a device holds. The kernel drops a
   key event that doesn't change the device's state: a release for a key it doesn't think is down
   is never seen by anyone.
2. **libinput**, in the Steam session's compositor (gamescope), per device too. It ignores "a
   release for a key it never saw pressed" and "a press for a key it thinks is down". On device
   removal it releases every key that device holds.
3. **gamescope's keyboard state** (xkbcommon). Each modifier key has a filter counting its
   presses: a press adds one, a release takes one, the modifier clears at zero. A release that
   went to another client (focus moved while the key was down: into the VR dashboard, say)
   leaves the count at one for good. Every later press and release of that key goes 2 → 1, so
   the key seems to do nothing while the modifier stays on. gamescope sends its modifier state
   to the nested desktop with every key.
4. **The nested desktop (KWin)**, a Wayland client of gamescope. It keeps its own xkbcommon
   state but takes the parent's modifier mask over it, so whatever gamescope says is held, the
   desktop and its apps see as held. Xwayland (`:2`) gets the same.
5. **The app.**

## What was tried, and why it couldn't work

- Releasing the modifier through the keyboard's own device node, as `release_held_keys` does:
  the kernel saw the key up already and dropped the event (layer 1). That path works only when
  the kernel still has the key down, which is the Bluetooth-lost-release case Unstick was made for.
- Pressing and releasing each modifier from ydotool (`clear_stuck_modifiers`): reaches
  gamescope, but 2 → 1 on its press counter (layer 3). It helps when the desktop alone lost the
  release and the compositor's count was right.
- A fresh uinput device that presses the key and is then removed while it's down: libinput
  synthesizes the release (layer 2), so again a press and a release, 2 → 1.
- XTEST key releases into the nested Xwayland: they reach KWin's own state, which the parent's
  modifier mask overrides at the next key (layer 4).
- Reloading the desktop's keymap (a `kxkbrc` change): same, the parent's mask wins.
- Powering the keyboard off and on: a new device, but the stuck count is in the compositor's
  shared state, not the device's.
- Caps Lock kept toggling throughout: it's a lock, not a press count.

What cleared it: `steamvr restart`, which restarts gamescope and its keyboard state. Every
earlier time the user had hit this, that was the fix too.

## What Unstick can say

It knows one thing for sure: whether any device still holds a key (layer 1). When none does and
the desktop still acts as if a modifier were held, the state is in the compositor, and only a
SteamVR restart lets go of it. Unstick says so now, instead of reporting success.

## Open ideas

- gamescope could be asked for a keyboard state reset; it has no interface for that today. An
  upstream request would need the reproduction: hold Shift on a keyboard, move focus into the VR
  dashboard, release Shift there, come back.
- The Frame Tweaks window's ⟳ Restart SteamVR flow could be offered from Unstick's notification;
  `notify-send` has no actions, so that needs a different notifier or a pad button.
