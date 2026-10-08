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
WIDTH_DEFAULT, WIDTH_MIN, WIDTH_MAX, WIDTH_STEP = 0.45, 0.30, 2.0, 0.05
FORWARD, BELOW, TILT_DEG = 0.55, 0.30, 25     # reset: in front of you, below eye level, tilted up


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
        if config.get("vr_pose"):
            self.pose = config["vr_pose"]
            self.apply_pose()
        else:
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
    def apply_pose(self):
        self.ov.setOverlayTransformAbsolute(self.handle, openvr.TrackingUniverseStanding, _mat(self.pose))

    def reset_position(self):
        """In front of you, below eye level, facing you, tilted back like a tabletop keyboard."""
        pose = self.system.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, 1)[0]
        m = pose.mDeviceToAbsoluteTracking.m
        pos = [m[0][3], m[1][3], m[2][3]]
        fx, fz = -m[0][2], -m[2][2]                       # headset forward, flattened
        n = math.hypot(fx, fz) or 1.0
        fx, fz = fx / n, fz / n
        center = [pos[0] + fx * FORWARD, pos[1] - BELOW, pos[2] + fz * FORWARD]
        z = [-fx, 0.0, -fz]                               # overlay normal points back at you
        x = [-z[2], 0.0, z[0]]                            # right = up x z
        t = math.radians(TILT_DEG)                        # tilt: rotate y/z about x
        y = [z[0] * math.sin(t), math.cos(t), z[2] * math.sin(t)]
        z = [z[0] * math.cos(t), -math.sin(t), z[2] * math.cos(t)]
        self.pose = [[x[0], y[0], z[0], center[0]],
                     [x[1], y[1], z[1], center[1]],
                     [x[2], y[2], z[2], center[2]]]
        self.apply_pose()
        self.save()

    def set_width(self, value):
        self.width_m = round(min(WIDTH_MAX, max(WIDTH_MIN, value)), 2)
        self.ov.setOverlayWidthInMeters(self.handle, self.width_m)
        self.save()

    def step_width(self, steps):
        self.set_width(self.width_m + steps * WIDTH_STEP)

    def save(self):
        self.config["width_m"] = self.width_m
        self.config["vr_pose"] = self.pose
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
        ev = openvr.VREvent_t()
        while self.ov.pollNextOverlayEvent(self.handle, ev):
            t, dev = ev.eventType, ev.trackedDeviceIndex
            self.last_device = dev
            if t == openvr.VREvent_MouseMove:
                pos = self.to_widget(ev.data.mouse)
                if self.drag is not None:
                    self.drag_to(pos)
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
                    self.drag = (pos, [row[:] for row in self.pose])
            elif t == openvr.VREvent_MouseButtonUp:
                pos = self.to_widget(ev.data.mouse)
                if self.pressed is not None:
                    self.send(self.pressed, QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.NoButton)
                    self.pressed = None
                if self.drag is not None:
                    self.drag = None
                    self.save()
            self.dirty = True
        if self.dirty and visible:
            self.render()

    def drag_to(self, pos):
        """Keep the grabbed point under the laser: the panel moves with it, in its own plane.
        (Mouse coordinates are relative to the moving panel, so correct by the offset from
        the grab point each time instead of using the total distance.)"""
        grab, _ = self.drag
        per_px = self.width_m / max(1, self.size[0])
        dx, dy = (pos.x() - grab.x()) * per_px, -(pos.y() - grab.y()) * per_px
        for r in range(3):              # along the overlay's own x and y axes
            self.pose[r][3] += self.pose[r][0] * dx + self.pose[r][1] * dy
        self.apply_pose()

    def close(self):
        try:
            self.ov.destroyOverlay(self.handle)
        except Exception:
            pass

    def dump(self):
        return json.dumps({"width_m": self.width_m})
