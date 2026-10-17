"""SteamVR pieces shared by Arrow Pad's VR panel, Screen snip's narration panel and the installer
window (installed beside i18n.py: lib/common.sh install_i18n). Each takes the openvr module, so
importing this needs no SteamVR.

- Poses: 3x4 rigid transforms as lists of rows (rotation | translation).
- Haptics: a direct pulse to the controller, which reaches it while the dashboard has input
  focus (SteamVR Input's vibration doesn't). TICK: Arrow Pad's and Full Keyboard's feel.
- GripReader: grip squeezes, read the way Full Keyboard reads them.
- note_image: the picture of the note shown under a panel (why it only slides: Steam's keyboard
  open), drawn with Qt (imported only then).
- DashboardGrab: SteamVR's own grab bar under a panel while Steam's keyboard is open (the VR
  environment helper's panel-grab patch), through files in the runtime folder."""
import json
import math
import os
import time
from pathlib import Path

TICK = {"hover": 1000, "press": 3999}        # µs: a light tick on hover, a firmer one on a press
NOTE_PX, NOTE_PAD_PX, NOTE_FONT_PX = 900, 28, 34     # a note's picture: width, margin, text size


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


def note_image(text):
    """A note's picture: text in a dark rounded box, as wide as NOTE_PX and as tall as it needs."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter
    from PyQt6.QtWidgets import QApplication
    if QApplication.instance() is None:         # (Qt ends the program on fonts without one)
        raise RuntimeError("a note's picture needs a running QApplication")
    font = QFont(QApplication.font())
    font.setPixelSize(NOTE_FONT_PX)
    flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
    inner = NOTE_PX - 2 * NOTE_PAD_PX
    h = int(QFontMetricsF(font).boundingRect(QRectF(0, 0, inner, 10000), flags, text).height()) + 2 * NOTE_PAD_PX
    img = QImage(NOTE_PX, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(11, 16, 22, 235))
    painter.drawRoundedRect(QRectF(0, 0, NOTE_PX, h), 22, 22)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(QRectF(NOTE_PAD_PX, NOTE_PAD_PX, inner, h - 2 * NOTE_PAD_PX), flags, text)
    painter.end()
    return img


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


def quat_of(rows):
    """{w, x, y, z} of a pose's rotation (rows of a 3x4 rigid transform)."""
    m = rows
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        k = math.sqrt(tr + 1.0) * 2
        q = (0.25 * k, (m[2][1] - m[1][2]) / k, (m[0][2] - m[2][0]) / k, (m[1][0] - m[0][1]) / k)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        k = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = ((m[2][1] - m[1][2]) / k, 0.25 * k, (m[0][1] + m[1][0]) / k, (m[0][2] + m[2][0]) / k)
    elif m[1][1] > m[2][2]:
        k = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][2] - m[2][0]) / k, (m[0][1] + m[1][0]) / k, 0.25 * k, (m[1][2] + m[2][1]) / k)
    else:
        k = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[1][0] - m[0][1]) / k, (m[0][2] + m[2][0]) / k, (m[1][2] + m[2][1]) / k, 0.25 * k)
    return dict(zip("wxyz", q))


def pose_of(t, q):
    """A 3x4 rigid transform (rows) from a translation {x, y, z} and a rotation {w, x, y, z}
    (normalised here); None if either isn't one."""
    try:
        w, x, y, z = (float(q[k]) for k in "wxyz")
        tx, ty, tz = (float(t[k]) for k in "xyz")
    except (KeyError, TypeError, ValueError):
        return None
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if not all(math.isfinite(v) for v in (n, tx, ty, tz)) or n < 1e-6 or max(abs(tx), abs(ty), abs(tz)) > 100:
        return None
    w, x, y, z = w / n, x / n, y / n, z / n
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), tx],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), ty],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), tz]]


class DashboardGrab:
    """SteamVR's own grab bar under a Frame Tweaks panel while Steam's keyboard is open. The
    keyboard hides where the controllers are from other programs (its keyboard privacy), so then
    a panel can only slide after the laser; SteamVR's dashboard can still move things. The VR
    environment helper's panel-grab patch draws SteamVR's grab bar under the panel, and while it's
    held a picture of the panel follows the hand (SteamVR moves it: no controller pose comes here).
    The panel hides meanwhile, and is told only where it was let go.

    Through files in the runtime folder, which the helper's service (sft-dashboard) relays:
      PANELS/KEY.json       from the panel (announce): {pid, t, r, w, h, visible, picture}
      PANELS/KEY.grab.json  to the panel (poll): {seq, state: held | dropped, t, r}
    Without the helper nothing reads them, and nothing changes."""
    PANELS = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}") / "frame-tweaks/panels"
    EVERY_S = 0.2                         # (a moving panel says where it is at most this often)

    def __init__(self, key, folder=None):
        self.folder = Path(folder) if folder else self.PANELS
        self.file, self.grab_file = self.folder / f"{key}.json", self.folder / f"{key}.grab.json"
        self.said, self.pending, self.said_at, self.seen = None, None, 0.0, None
        try:
            self.grab_file.unlink(missing_ok=True)      # (an earlier run's: not for this one)
        except OSError:
            pass

    def announce(self, pose, width, height, visible, picture=None, now=False):
        """Where the panel is (pose: rows, centre), its size in metres, whether it shows, and its
        current picture (a PNG in the runtime folder, which the service can read). Written when it
        changed; at most every EVERY_S unless now (poll() writes what waited)."""
        if not pose or width <= 0 or height <= 0:
            return
        state = {"pid": os.getpid(), "t": {k: round(pose[i][3], 4) for i, k in enumerate("xyz")},
                 "r": {k: round(v, 5) for k, v in quat_of(pose).items()},
                 "w": round(width, 4), "h": round(height, 4), "visible": bool(visible), "picture": picture or ""}
        if state == self.said:
            self.pending = None
            return
        if not now and time.monotonic() - self.said_at < self.EVERY_S:
            self.pending = state
            return
        self._write(state)

    def _write(self, state):
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            tmp = self.file.with_name(f".{self.file.name}.tmp")
            tmp.write_text(json.dumps(state))
            tmp.replace(self.file)
        except OSError:
            return
        self.said, self.pending, self.said_at = state, None, time.monotonic()

    def poll(self):
        """What the bar did since the last look: ("held", None), ("dropped", pose rows, or None
        to stay where it was), or None. (Also writes an announcement that had to wait.)"""
        if self.pending is not None and time.monotonic() - self.said_at >= self.EVERY_S:
            self._write(self.pending)
        try:
            data = json.loads(self.grab_file.read_text())
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or data.get("seq") == self.seen:
            return None
        self.seen = data.get("seq")
        if data.get("state") == "held":
            return "held", None
        if data.get("state") == "dropped":
            return "dropped", pose_of(data.get("t"), data.get("r"))
        return None

    def close(self):
        for f in (self.file, self.grab_file):
            try:
                f.unlink(missing_ok=True)
            except OSError:
                pass
