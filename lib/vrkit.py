"""SteamVR pieces shared by Arrow Pad's VR panel, Screen snip's narration panel and the installer
window (installed beside i18n.py: lib/common.sh install_i18n). Each takes the openvr module, so
importing this needs no SteamVR.

- Poses: 3x4 rigid transforms as lists of rows (rotation | translation).
- Haptics: a direct pulse to the controller, which reaches it while the dashboard has input
  focus (SteamVR Input's vibration doesn't). TICK: Arrow Pad's and Full Keyboard's feel.
- GripReader: grip squeezes, read the way Full Keyboard reads them."""
import math

TICK = {"hover": 1000, "press": 3999}        # µs: a light tick on hover, a firmer one on a press


def rigid_mul(a, b):
    """a * b for two rigid 3x4 transforms."""
    return [[sum(a[r][k] * b[k][c] for k in range(3)) + (a[r][3] if c == 3 else 0.0)
             for c in range(4)] for r in range(3)]


def rigid_inv(a):
    rt = [[a[c][r] for c in range(3)] for r in range(3)]          # rotation transposed
    t = [-sum(rt[r][k] * a[k][3] for k in range(3)) for r in range(3)]
    return [rt[r] + [t[r]] for r in range(3)]


def relative(a, b):
    """a^-1 * b: b as seen from a (e.g. a panel's pose relative to the controller holding it)."""
    return rigid_mul(rigid_inv(a), b)


def hmd34(vr, rows):
    """rows as openvr's HmdMatrix34_t."""
    m = vr.HmdMatrix34_t()
    for r in range(3):
        for c in range(4):
            m.m[r][c] = rows[r][c]
    return m


def dashboard_device(vr):
    """The controller driving the dashboard's laser (else the right hand's), or None."""
    dev = vr.VROverlay().getPrimaryDashboardDevice()
    if dev == vr.k_unTrackedDeviceIndexInvalid:
        dev = vr.VRSystem().getTrackedDeviceIndexForControllerRole(vr.TrackedControllerRole_RightHand)
    return None if dev == vr.k_unTrackedDeviceIndexInvalid else dev


def direct_pulse(vr, system, device, us):
    """A haptic pulse of us microseconds (at most 3999) on that device; False without one."""
    if device is None or device == vr.k_unTrackedDeviceIndexInvalid:
        return False
    system.triggerHapticPulse(device, 0, int(max(1, min(3999, us))))
    return True


class GripReader:
    """Grip squeezes, read the way Full Keyboard reads them: the Frame's dashboard hides grip
    actions and legacy controller state from apps, but the controller model's "button_grip"
    part still moves. Its rotation from the rest pose, in degrees, with Full Keyboard's latch:
    held from 1.0°, released below 0.5°, armed only after a released sample."""

    def __init__(self, vr):
        self.vr = vr
        self.sys, self.rm, self.inp = vr.VRSystem(), vr.VRRenderModels(), vr.VRInput()
        self.hands = [{"role": role, "path": self.inp.getInputSourceHandle(f"/user/hand/{hand}"),
                       "armed": False, "held": False, "device": None}
                      for hand, role in (("left", vr.TrackedControllerRole_LeftHand),
                                         ("right", vr.TrackedControllerRole_RightHand))]

    @staticmethod
    def _angle(a, b):
        tr = sum(a.m[r][c] * b.m[r][c] for r in range(3) for c in range(3))
        return math.degrees(math.acos(max(-1.0, min(1.0, (tr - 1) / 2))))

    def poll(self):
        """[(device, held, just_pressed)] for each connected controller."""
        vr, out = self.vr, []
        for h in self.hands:
            try:
                d = self.sys.getTrackedDeviceIndexForControllerRole(h["role"])
                if d == vr.k_unTrackedDeviceIndexInvalid or not self.sys.isTrackedDeviceConnected(d):
                    h.update(armed=False, held=False, device=None)
                    continue
                if d != h["device"]:
                    h.update(armed=False, held=False, device=d)
                model = self.sys.getStringTrackedDeviceProperty(d, vr.Prop_RenderModelName_String)
                mode = vr.RenderModel_ControllerMode_State_t()
                ok1, cur = self.rm.getComponentStateForDevicePath(model, "button_grip", h["path"], mode)
                ok2, rest = self.rm.getComponentState(model, "button_grip", vr.VRControllerState_t(), mode)
                if not (ok1 and ok2):
                    h.update(armed=False, held=False)
                    continue
                a = self._angle(rest.mTrackingToComponentRenderModel, cur.mTrackingToComponentRenderModel)
            except Exception:
                h.update(armed=False, held=False)
                continue
            if not h["armed"]:
                h["armed"] = a < 0.5
                continue
            held = a >= (0.5 if h["held"] else 1.0)
            out.append((d, held, held and h["held"] is False))
            h["held"] = held
        return out

    def pause(self):
        """Not read for a while (no laser on the panel): the next read says whether each grip is
        held, but a grip squeezed meanwhile (carrying a window, say) isn't a new squeeze."""
        for h in self.hands:
            if h["armed"]:                      # (unarmed, it's released when it arms: not stale)
                h["held"] = None
