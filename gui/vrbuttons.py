"""Steam Frame controller buttons for the installer window in VR: B = back, Y = home (the list,
scrolled to the top), A = tick/untick the row the laser points at, left D-pad up/down = move a
highlight through the rows; and haptic ticks for its buttons.

The window is a Steam floating window, which gets the laser as a mouse but never the
controller's buttons, and on the Frame SteamVR hands button actions only to the app with focus
(test actions bound for a background app, an overlay app, and an overlay app owning an overlay
never became active). So the buttons are read from their parts in the controller's model
(lib/vrkit.py ButtonReader), which report a press whatever has focus, and only while the laser
is on the window: a press elsewhere is someone else's. They can't be taken from SteamVR's laser
mouse, which gets them too; on the Frame it sends the window nothing for A, B and Y, and arrow
keys for the D-pad (the window ignores those just after a D-pad press it handled: see
recent_dpad).
Optional: does nothing without SteamVR or the openvr module."""
import time

import vrkit  # (lib/: on the window's sys.path)

# Which part of the controller each action reads.
BUTTONS = {"back": ("right", "button_b"), "home": ("right", "button_y"), "toggle": ("right", "button_a"),
           "up": ("left", "dpad_up"), "down": ("left", "dpad_down")}


class VRButtons:
    def __init__(self, handlers):
        self.handlers = handlers            # {"back": fn, "home": fn, "toggle": fn, "up": fn, "down": fn}
        self.ok = False                     # the buttons are read (SteamVR up, some handlers)
        self.started = False                # SteamVR is up: haptics work even if the buttons stop
        self.claimed = False                # (nothing is claimed any more: kept for the window's timer)
        self.down, self.dpad_at = {}, 0.0
        try:
            import openvr
            self.vr = openvr
            openvr.init(openvr.VRApplication_Overlay)
            self.started = True
            self.readers = {n: vrkit.ButtonReader(openvr, *BUTTONS[n]) for n in handlers if n in BUTTONS}
            self.ok = bool(self.readers)
        except Exception:
            self.ok = False

    def poll(self, hovered):
        """Call ~30 times a second; hovered: the laser is over the window. A button acts when it
        goes down while the laser is on the window; one already held when the laser arrives
        doesn't."""
        if not self.ok:
            return
        try:
            for name, reader in self.readers.items():
                down = bool(reader.pressed())
                was = self.down.get(name)
                self.down[name] = down
                if down and was is False and hovered:
                    if name in ("up", "down"):
                        self.dpad_at = time.monotonic()
                    self.handlers[name]()
        except Exception:
            self.ok = False

    def recent_dpad(self, seconds=0.4):
        """A D-pad press was handled just now (so the arrow key SteamVR also sends is ignored)."""
        return self.ok and time.monotonic() - self.dpad_at < seconds

    def haptic(self, kind):
        """A tick (hover) or a firmer pulse (press) on the controller driving the laser, as on
        Arrow Pad and Full Keyboard. A direct pulse: SteamVR Input haptics need input focus,
        which the dashboard has."""
        # (not tied to self.ok: an error reading the buttons used to turn haptics off too, for good)
        if not self.started:
            return
        try:
            vrkit.direct_pulse(self.vr, self.vr.VRSystem(), vrkit.dashboard_device(self.vr), vrkit.TICK[kind])
        except Exception:
            pass

    def close(self):
        if self.started:
            try:
                self.vr.shutdown()
            except Exception:
                pass
