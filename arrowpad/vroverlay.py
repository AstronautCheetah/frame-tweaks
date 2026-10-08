"""Arrow Pad as a native SteamVR overlay (VR mode), the way Full Keyboard works.

A floating *window* takes keyboard focus when you click it in VR (gamescope ignores the
"don't focus me" hint and won't hand focus back), so its keys went to itself. An overlay never
takes focus: the pad is drawn off-screen, shown as an overlay texture, and the SteamVR laser's
mouse events are fed back into its buttons. Keys then reach the app you were using, and
haptics go to the controller that's pointing (an overlay being pointed at has input focus).

Like Full Keyboard: visible while the dashboard is, Reset puts it in front of you, +/- change
its width in 5 cm steps (0.30–2 m), drag the panel to move it, Pin stops that.
"""
import ctypes
import json
import math

import openvr
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PyQt6.QtGui import QImage, QMouseEvent
from PyQt6.QtWidgets import QApplication, QPushButton

KEY = "steam-frame-tweaks.arrowpad"
MAX_DISTANCE = 4.0       # metres from the headset; further than that, bring it back
WIDTH_DEFAULT, WIDTH_MIN, WIDTH_MAX, WIDTH_STEP = 0.55, 0.30, 2.0, 0.05
# Placement like Full Keyboard: anchored to Steam's dashboard (its main panel while visible, else
# the dashboard bar), top edge 6 cm below its bottom centre, 24 cm toward you, tilted back 50°.
# The pad keeps that offset *relative to the dashboard*, so it follows the dashboard around
# (recentering, moving it, a re-centred play space), as Full Keyboard does.
DASHBOARD = ("valve.steam.gamepadui.main", "valve.steam.gamepadui.bar")
GAP_BELOW, TOWARD_VIEWER, PITCH_DEG = 0.06, 0.24, 50
FORWARD, BELOW = 0.55, 0.30          # fallback without a dashboard: in front of the headset


def _rigid_mul(a, b):
    """Compose two 3x4 rigid transforms (rotation | translation)."""
    return [[sum(a[r][k] * b[k][c] for k in range(3)) + (a[r][3] if c == 3 else 0.0)
             for c in range(4)] for r in range(3)]


def _rigid_inv(a):
    rt = [[a[c][r] for c in range(3)] for r in range(3)]          # rotation transposed
    t = [-sum(rt[r][k] * a[k][3] for k in range(3)) for r in range(3)]
    return [rt[r] + [t[r]] for r in range(3)]


def _mat(rows):
    m = openvr.HmdMatrix34_t()
    for r in range(3):
        for c in range(4):
            m.m[r][c] = rows[r][c]
    return m


class OverlayHost:
    def __init__(self, pad, config):
        self.pad = pad
        self.config = config            # dict persisted by the pad (pos/scale/pinned/...)
        openvr.init(openvr.VRApplication_Overlay)
        self.ov = openvr.VROverlay()
        self.system = openvr.VRSystem()
        self.handle = self.ov.createOverlay(KEY, "Arrow Pad")
        self.ov.setOverlayInputMethod(self.handle, openvr.VROverlayInputMethod_Mouse)
        self.ov.setOverlaySortOrder(self.handle, 10)
        self.width_m = float(config.get("width_m", WIDTH_DEFAULT))
        self.ov.setOverlayWidthInMeters(self.handle, self.width_m)
        self.hover = None               # button under the laser
        self.pressed = None             # button being pressed
        self.drag = None                # (grab pixel, start transform) while dragging the panel
        self.last_device = None         # controller behind the latest laser event
        self.size = (0, 0)
        self.dirty = True
        self.offset = config.get("vr_offset")       # pose relative to the dashboard anchor
        self.pose = None
        if not (self.offset and self.follow_dashboard()) or self.distance_from_head() > MAX_DISTANCE:
            self.reset_position()
        self.visible = False
        QTimer(pad, interval=11, timeout=self.poll).start()      # ~90 Hz event pump
        QTimer(pad, interval=100, timeout=self.mark_dirty).start()   # state changes (mic etc.)

    # ---- rendering ------------------------------------------------------
    def mark_dirty(self):
        self.dirty = True

    def render(self):
        img = self.pad.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        w, h = img.width(), img.height()
        data = bytes(img.constBits().asstring(img.sizeInBytes()))
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        self.ov.setOverlayRaw(self.handle, buf, w, h, 4)
        if (w, h) != self.size:
            self.size = (w, h)
            scale = openvr.HmdVector2_t()
            scale.v[0], scale.v[1] = w, h
            self.ov.setOverlayMouseScale(self.handle, scale)
        self.dirty = False

    # ---- placement --------------------------------------------------------
    def device_matrix(self, index):
        poses = self.system.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0,
                                                            openvr.k_unMaxTrackedDeviceCount)
        if index is None or index >= len(poses) or not poses[index].bPoseIsValid:
            return None
        m = poses[index].mDeviceToAbsoluteTracking.m
        return [[m[r][c] for c in range(4)] for r in range(3)]

    def dashboard_anchor(self):
        """Bottom centre of the visible dashboard (main panel, else the bar) as a rigid 3x4
        transform with its scale removed; None if neither is available."""
        for key in DASHBOARD:
            try:
                h = self.ov.findOverlay(key)
                if key.endswith(".main") and not self.ov.isOverlayVisible(h):
                    continue      # hidden main panel keeps a stale transform (Full Keyboard's note)
                scale = self.ov.getOverlayMouseScale(h)
                at = openvr.HmdVector2_t()
                at.v[0], at.v[1] = scale.v[0] / 2, 0.0          # bottom centre (origin bottom-left)
                r = self.ov.getTransformForOverlayCoordinates(h, openvr.TrackingUniverseStanding, at)
                m = (r.m if hasattr(r, "m") else r[-1].m)
                rows = [[m[i][j] for j in range(4)] for i in range(3)]
                for c in range(3):                               # normalise the scaled basis
                    n = math.sqrt(sum(rows[i][c] ** 2 for i in range(3))) or 1.0
                    for i in range(3):
                        rows[i][c] /= n
                return rows
            except Exception:
                continue
        return None

    def follow_dashboard(self):
        """Pose = dashboard anchor x stored offset. False if there's no anchor."""
        anchor = self.dashboard_anchor()
        if anchor is None or not self.offset:
            return False
        pose = _rigid_mul(anchor, self.offset)
        if pose != self.pose:
            self.pose = pose
            self.apply_pose()
        return True

    def remember_offset(self):
        anchor = self.dashboard_anchor()
        if anchor is not None and self.pose:
            self.offset = _rigid_mul(_rigid_inv(anchor), self.pose)

    def distance_from_head(self):
        head = self.device_matrix(openvr.k_unTrackedDeviceIndex_Hmd)
        if head is None or not self.pose:
            return 0.0
        return math.dist([head[r][3] for r in range(3)], [self.pose[r][3] for r in range(3)])

    def apply_pose(self):
        self.ov.setOverlayTransformAbsolute(self.handle, openvr.TrackingUniverseStanding, _mat(self.pose))

    def reset_position(self):
        """Beneath the dashboard like Full Keyboard (or in front of the headset without one)."""
        anchor = self.dashboard_anchor()
        h_m = self.width_m * (self.size[1] / self.size[0] if self.size[0] else 0.8)
        t = math.radians(PITCH_DEG)
        if anchor is not None:
            # Upright frame from the anchor: its left-right axis, true vertical, and "toward you"
            # horizontal. (The dashboard bar is tilted back like a tray; Full Keyboard pitches
            # 50° from upright regardless of what it's anchored to.)
            ax = [anchor[0][0], 0.0, anchor[2][0]]
            n = math.hypot(ax[0], ax[2]) or 1.0
            ax = [ax[0] / n, 0.0, ax[2] / n]
            ay = [0.0, 1.0, 0.0]
            az = [-ax[2], 0.0, ax[0]]                           # = ax x up, horizontal
            if az[0] * anchor[0][2] + az[2] * anchor[2][2] < 0:   # point it toward the viewer
                az = [-az[0], 0.0, -az[2]]
                ax = [-ax[0], 0.0, -ax[2]]
            org = [anchor[i][3] for i in range(3)]
        else:
            head = self.device_matrix(openvr.k_unTrackedDeviceIndex_Hmd)
            fx, fz = -head[0][2], -head[2][2]
            n = math.hypot(fx, fz) or 1.0
            fx, fz = fx / n, fz / n
            az, ay, ax = [-fx, 0.0, -fz], [0.0, 1.0, 0.0], [fz, 0.0, -fx]
            org = [head[0][3] + fx * FORWARD, head[1][3] - BELOW + GAP_BELOW, head[2][3] + fz * FORWARD]
        # tilt back: rotate about the anchor's x axis so the top leans away from you
        y = [ay[i] * math.cos(t) - az[i] * math.sin(t) for i in range(3)]
        z = [ay[i] * math.sin(t) + az[i] * math.cos(t) for i in range(3)]
        # top edge GAP_BELOW under the anchor, centre TOWARD_VIEWER closer to you
        centre = [org[i] - ay[i] * GAP_BELOW - y[i] * (h_m / 2) + az[i] * TOWARD_VIEWER for i in range(3)]
        self.pose = [[ax[i], y[i], z[i], centre[i]] for i in range(3)]
        self.apply_pose()
        self.remember_offset()
        self.save()

    def set_width(self, value):
        self.width_m = round(min(WIDTH_MAX, max(WIDTH_MIN, value)), 2)
        self.ov.setOverlayWidthInMeters(self.handle, self.width_m)
        self.save()

    def step_width(self, steps):
        self.set_width(self.width_m + steps * WIDTH_STEP)

    def save(self):
        self.config["width_m"] = self.width_m
        self.config["vr_offset"] = self.offset
        self.config.pop("vr_pose", None)      # absolute poses go stale when the play space moves
        self.pad.save_config()

    # ---- input -------------------------------------------------------------
    def to_widget(self, mouse):
        """Overlay mouse coords (origin bottom-left, scaled to pixels) -> widget point."""
        return QPoint(int(mouse.x), int(self.size[1] - mouse.y))

    def send(self, widget, etype, pos, buttons):
        local = widget.mapFrom(self.pad, pos) if widget is not self.pad else pos
        ev = QMouseEvent(etype, QPointF(local), QPointF(self.pad.mapToGlobal(pos)),
                         Qt.MouseButton.LeftButton, buttons, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(widget, ev)

    def button_at(self, pos):
        w = self.pad.childAt(pos)
        while w is not None and not isinstance(w, QPushButton):
            w = w.parentWidget()
        return w

    def set_hover(self, button, device):
        if button is self.hover:
            return
        if self.hover is not None:
            self.hover.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
            QApplication.sendEvent(self.hover, QEvent(QEvent.Type.Leave))
            self.hover.update()
        self.hover = button
        if button is not None:
            button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, True)
            QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))   # hover haptic filter
            button.update()
            if button.property("tool") != "true":
                self.pad.pulse("hover", device)
        self.dirty = True

    def poll(self):
        visible = bool(self.ov.isDashboardVisible())
        if visible != self.visible:
            (self.ov.showOverlay if visible else self.ov.hideOverlay)(self.handle)
            self.visible = visible
        if visible and self.drag is None:
            self.follow_dashboard()             # ride along with the dashboard
        ev = openvr.VREvent_t()
        while self.ov.pollNextOverlayEvent(self.handle, ev):
            t, dev = ev.eventType, ev.trackedDeviceIndex
            self.last_device = dev
            if t == openvr.VREvent_MouseMove:
                pos = self.to_widget(ev.data.mouse)
                if self.drag is not None:
                    self.drag_follow()
                else:
                    self.set_hover(self.button_at(pos), dev)
                    if self.pressed is not None:
                        self.send(self.pressed, QEvent.Type.MouseMove, pos, Qt.MouseButton.LeftButton)
            elif t == openvr.VREvent_MouseButtonDown:
                pos = self.to_widget(ev.data.mouse)
                b = self.button_at(pos)
                if b is not None:
                    self.pressed = b
                    self.send(b, QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton)
                elif not self.pad.pinned:
                    # Grab: the panel follows the controller rigidly, like Full Keyboard's grip
                    # grab. (Moving it by laser coordinates on the panel ran away.)
                    ctrl = self.device_matrix(dev)
                    if ctrl is not None:
                        self.drag = (dev, _rigid_mul(_rigid_inv(ctrl), self.pose))
            elif t == openvr.VREvent_MouseButtonUp:
                pos = self.to_widget(ev.data.mouse)
                if self.pressed is not None:
                    self.send(self.pressed, QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.NoButton)
                    self.pressed = None
                if self.drag is not None:
                    self.drag = None
                    if self.distance_from_head() > MAX_DISTANCE:
                        self.reset_position()
                    else:
                        self.remember_offset()     # the new spot, relative to the dashboard
                    self.save()
            self.dirty = True
        if self.dirty and visible:
            self.render()

    def drag_follow(self):
        """While grabbed: overlay = controller now x (controller at grab)^-1 x overlay at grab."""
        dev, offset = self.drag
        ctrl = self.device_matrix(dev)
        if ctrl is not None:
            self.pose = _rigid_mul(ctrl, offset)
            self.apply_pose()

    def close(self):
        try:
            self.ov.destroyOverlay(self.handle)
        except Exception:
            pass

    def dump(self):
        return json.dumps({"width_m": self.width_m})
