"""Controller haptics for Arrow Pad through SteamVR Input, like Full Keyboard: a light tick
when the laser moves onto a key, a firmer click on press, on the hand doing the pointing.
Optional: does nothing without SteamVR or the openvr module."""
import math
import os
from pathlib import Path

VR_DIR = Path(__file__).resolve().parent / "vr"
# Full Keyboard's feedback: hover 4 ms at 10 % / 240 Hz, press 25 ms at full strength / 150 Hz.
HOVER = (0.004, 240, 0.10)
PRESS = (0.025, 150, 1.0)


class Haptics:
    def __init__(self):
        self.ok = False
        try:
            import openvr
            self.vr_mod = openvr
            self.system = openvr.init(openvr.VRApplication_Overlay)
            self.input = openvr.VRInput()
            self.input.setActionManifestPath(str(VR_DIR / "actions.json"))
            self.set = self.input.getActionSetHandle("/actions/arrowpad")
            self.out = {h: self.input.getActionHandle(f"/actions/arrowpad/out/haptic_{h}")
                        for h in ("left", "right")}
            self.active = openvr.VRActiveActionSet_t()
            self.active.ulActionSet = self.set
            self.ok = True
        except Exception:      # no SteamVR running, no openvr module, …
            self.ok = False

    def pointing_hand(self):
        """The hand turning faster right now is the one sweeping the laser."""
        vr = self.vr_mod
        poses = self.system.getDeviceToAbsoluteTrackingPose(vr.TrackingUniverseStanding, 0,
                                                            vr.k_unMaxTrackedDeviceCount)
        best, speed = "right", -1.0
        for hand, role in (("left", vr.TrackedControllerRole_LeftHand),
                           ("right", vr.TrackedControllerRole_RightHand)):
            i = self.system.getTrackedDeviceIndexForControllerRole(role)
            if i == vr.k_unTrackedDeviceIndexInvalid or not poses[i].bPoseIsValid:
                continue
            w = poses[i].vAngularVelocity.v
            s = math.sqrt(w[0] ** 2 + w[1] ** 2 + w[2] ** 2)
            if s > speed:
                best, speed = hand, s
        return best

    def pulse(self, kind):
        if not self.ok:
            return
        try:
            duration, freq, amp = HOVER if kind == "hover" else PRESS
            self.input.updateActionState([self.active])
            self.input.triggerHapticVibrationAction(self.out[self.pointing_hand()], 0, duration, freq,
                                                    amp, self.vr_mod.k_ulInvalidInputValueHandle)
        except Exception:
            self.ok = False    # SteamVR went away: stop trying

    def close(self):
        if self.ok:
            try:
                self.vr_mod.shutdown()
            except Exception:
                pass
