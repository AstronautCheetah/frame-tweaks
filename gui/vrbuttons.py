"""Steam Frame controller buttons for the installer window in VR: B = back, Y = home,
A = tick/untick the row the laser points at; and haptic ticks for its buttons.

The window is a Steam floating window, which gets the laser as a mouse but never the
controller's buttons. So, while the laser is over the window, this claims A, B and Y through
SteamVR Input with an overlay-global action set priority (which receives input whatever has
focus, and holds it from other apps), and releases them as soon as the laser leaves.
SteamVR keys action manifests by program name, and Arrow Pad also runs under Python, so
install.sh starts the window with a copy of the interpreter named `sft-python`: its own app
key ("system.generated.sft-python"), its own bindings. (Registering a custom app key with
IVRApplications doesn't work on the Frame.)
Optional: does nothing without SteamVR or the openvr module."""
from pathlib import Path

import vrkit  # (lib/: on the window's sys.path)

VR_DIR = Path(__file__).resolve().parent / "vr"


class VRButtons:
    def __init__(self, handlers):
        self.handlers = handlers            # {"back": fn, "home": fn, "toggle": fn}
        self.ok, self.claimed = False, False
        self.started = False                # SteamVR is up: haptics work even if the buttons stop
        try:
            import openvr
            self.vr = openvr
            openvr.init(openvr.VRApplication_Overlay)
            self.started = True
            if not handlers:                # haptics only: the buttons stay with whatever has focus
                return
            self.input = openvr.VRInput()
            self.input.setActionManifestPath(str(VR_DIR / "actions.json"))
            self.set = openvr.VRActiveActionSet_t()
            self.set.ulActionSet = self.input.getActionSetHandle("/actions/sft")
            self.set.nPriority = openvr.k_nActionSetOverlayGlobalPriorityMin
            self.actions = {n: self.input.getActionHandle(f"/actions/sft/in/{n}") for n in handlers}
            self.ok = True
        except Exception:
            self.ok = False

    def poll(self, hovered):
        """Call ~30 times a second; hovered: the laser is over the window."""
        if not self.ok:
            return
        try:
            if not hovered:
                if self.claimed:            # hand the buttons back
                    self.input.updateActionState([])
                    self.claimed = False
                return
            self.input.updateActionState([self.set])
            first = not self.claimed
            self.claimed = True
            for name, handle in self.actions.items():
                d = self.input.getDigitalActionData(handle, self.vr.k_ulInvalidInputValueHandle)
                if d.bActive and d.bChanged and d.bState and not first:
                    self.handlers[name]()
        except Exception:
            self.ok = False

    def haptic(self, kind):
        """A tick (hover) or a firmer pulse (press) on the controller driving the laser, as on
        Arrow Pad and Full Keyboard. A direct pulse: SteamVR Input haptics need input focus,
        which the dashboard has."""
        # (not tied to self.ok: an error claiming the buttons used to turn haptics off too, for good)
        if not self.started:
            return
        try:
            vrkit.direct_pulse(self.vr, self.vr.VRSystem(), vrkit.dashboard_device(self.vr), vrkit.TICK[kind])
        except Exception:
            pass

    def close(self):
        if self.started:
            try:
                if self.ok:
                    self.input.updateActionState([])
                self.vr.shutdown()
            except Exception:
                pass
