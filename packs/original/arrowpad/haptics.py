"""Controller haptics for Arrow Pad, like Full Keyboard: a light tick when the laser moves
onto a key, a firmer click on press, on the hand doing the pointing.

SteamVR delivers SteamVR Input haptics only to the app that has input focus. Full Keyboard
owns its VR overlay, so it does; our VR window is a Steam floating window, so the dashboard
has focus. We therefore also send the older direct pulse (IVRSystem.TriggerHapticPulse),
which isn't tied to input focus. Optional: does nothing without SteamVR or openvr."""
import math
import os
import time
from pathlib import Path

VR_DIR = Path(__file__).resolve().parent / "vr"
# Full Keyboard's feedback: hover 4 ms at 10 % / 240 Hz, press 25 ms at full strength / 150 Hz.
HOVER = (0.004, 240, 0.10)
PRESS = (0.025, 150, 1.0)
LOG = Path(f"/run/user/{os.getuid()}/arrowpad-haptics.log")


class Haptics:
    def __init__(self, already_initialised=False):
        self.ok, self.retry_at = False, 0.0
        try:
            import openvr
            self.vr_mod = openvr
            self.system = openvr.VRSystem() if already_initialised else openvr.init(openvr.VRApplication_Overlay)
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

    def pointing_index(self):
        """Tracked-device index of the pointing hand (see pointing_hand)."""
        vr = self.vr_mod
        role = (vr.TrackedControllerRole_LeftHand if self.pointing_hand() == "left"
                else vr.TrackedControllerRole_RightHand)
        return self.system.getTrackedDeviceIndexForControllerRole(role)

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

    def reconnect(self):
        """After an error: SteamVR's interfaces again (the pad keeps its own openvr session)."""
        vr = self.vr_mod
        self.system, self.input = vr.VRSystem(), vr.VRInput()
        self.input.setActionManifestPath(str(VR_DIR / "actions.json"))
        self.set = self.input.getActionSetHandle("/actions/arrowpad")
        self.out = {h: self.input.getActionHandle(f"/actions/arrowpad/out/haptic_{h}") for h in ("left", "right")}
        self.active.ulActionSet = self.set

    def pulse(self, kind, device=None, strength=1.0):
        """device: tracked-device index that caused it (overlay events say which); else guess.
        strength: 0-1, scales amplitude (the settings' Light / Normal)."""
        if strength <= 0 or not hasattr(self, "vr_mod"):
            return
        if not self.ok:              # an earlier error: try again every few seconds, not never
            if time.monotonic() < self.retry_at:
                return
            try:
                self.reconnect()
                self.ok = True
            except Exception as e:
                self.failed(e)
                return
        try:
            duration, freq, amp = HOVER if kind == "hover" else PRESS
            amp *= strength
            vr = self.vr_mod
            if device is not None and device != vr.k_unTrackedDeviceIndexInvalid:
                role = self.system.getControllerRoleForTrackedDeviceIndex(device)
                hand = "left" if role == vr.TrackedControllerRole_LeftHand else "right"
            else:
                hand = self.pointing_hand()
            # Direct pulse first: it's what reaches the controller here (not tied to input focus).
            # Duration in microseconds (max 3999); strength comes from the length, so scale it.
            idx = device if device not in (None, self.vr_mod.k_unTrackedDeviceIndexInvalid) else self.pointing_index()
            if idx != self.vr_mod.k_unTrackedDeviceIndexInvalid:
                self.system.triggerHapticPulse(idx, 0, int(min(3999, duration * 1e6) * max(0.25, amp)))
        except Exception as e:
            self.failed(e)
            return
        # SteamVR Input's vibration as well (it only arrives while we have input focus). It can be
        # refused (InputError_InvalidHandle, seen on the Frame); that used to abort the direct pulse
        # above, and then every pulse: now it's only noted, once.
        try:
            self.input.updateActionState([self.active])
            self.input.triggerHapticVibrationAction(self.out[hand], 0, duration, freq,
                                                    amp, self.vr_mod.k_ulInvalidInputValueHandle)
        except Exception as e:
            if not getattr(self, "action_noted", False):
                self.action_noted = True
                self.note(f"SteamVR Input vibration refused (direct pulses still sent): {type(e).__name__}")

    def failed(self, e):
        """Note it (LOG) and pause for 5 s; one error used to switch haptics off for good."""
        self.ok, self.retry_at = False, time.monotonic() + 5
        self.note(f"{type(e).__name__}: {e}")

    @staticmethod
    def note(text):
        try:
            with open(LOG, "a") as f:
                f.write(f"{time.strftime('%F %T')} haptics: {text}\n")
        except OSError:
            pass

    def close(self):
        if self.ok:
            try:
                self.vr_mod.shutdown()
            except Exception:
                pass
