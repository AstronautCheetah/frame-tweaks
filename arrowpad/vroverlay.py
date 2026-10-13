"""Arrow Pad as a native SteamVR overlay (VR mode), the way Full Keyboard works.

A floating *window* takes keyboard focus when you click it in VR (gamescope ignores the
"don't focus me" hint and won't hand focus back), so its keys went to itself. An overlay never
takes focus: the pad is drawn off-screen, shown as an overlay texture, and the SteamVR laser's
mouse events are fed back into its buttons. Keys then reach the app you were using, and
haptics go to the controller that's pointing (an overlay being pointed at has input focus).

Like Full Keyboard: visible while the dashboard is, Reset puts it in front of you, +/- change
its width in 5 cm steps (0.30–2 m), drag the panel to move it, Pin stops that.
"""
import hashlib
import json
import math
import os
import time

import openvr
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PyQt6.QtGui import QImage, QMouseEvent
from PyQt6.QtWidgets import QApplication, QPushButton

KEY = "steam-frame-tweaks.arrowpad"
# The texture goes to SteamVR as a PNG file (SetOverlayFromFile), not SetOverlayRaw: on the Frame
# raw uploads never showed (an invisible panel that still caught the laser), and a 2.5 MB raw
# upload crashed vrcompositor (SIGBUS). Capped size and rate keep the compositor's work small.
MAX_TEX = (1024, 768)
MIN_RENDER_INTERVAL = 0.15           # at most ~7 texture updates a second
SWAP_SHOW_MS, SWAP_HIDE_MS = 60, 50  # double buffering: load, show new, then hide old
DEPTH_GAIN = 3.0                     # dragging: push/pull moves the pad 3x as far; up/down/sideways 1:1
DEPTH_MIN, DEPTH_MAX = 0.25, 3.5     # dragging: keep the pad this far from your head (m, horizontally)
POSE_EPSILON = 0.0015                # ignore anchor jitter below 1.5 mm (and ~0.1°)
TEX_DIR = f"/run/user/{os.getuid()}"
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


class GripReader:
    """Grip squeezes, read the way Full Keyboard reads them: the Frame's dashboard hides grip
    actions and legacy controller state from apps, but the controller model's "button_grip"
    part still moves. Its rotation from the rest pose, in degrees, with Full Keyboard's latch:
    held from 1.0°, released below 0.5°, armed only after a released sample."""

    def __init__(self):
        self.sys, self.rm, self.inp = openvr.VRSystem(), openvr.VRRenderModels(), openvr.VRInput()
        self.hands = []
        for hand, role in (("left", openvr.TrackedControllerRole_LeftHand),
                           ("right", openvr.TrackedControllerRole_RightHand)):
            self.hands.append({"role": role, "path": self.inp.getInputSourceHandle(f"/user/hand/{hand}"),
                               "armed": False, "held": False, "device": None})

    @staticmethod
    def _angle(a, b):
        tr = sum(a.m[r][c] * b.m[r][c] for r in range(3) for c in range(3))
        return math.degrees(math.acos(max(-1.0, min(1.0, (tr - 1) / 2))))

    def poll(self):
        """[(device, held, just_pressed)] for each connected controller."""
        out = []
        for h in self.hands:
            try:
                d = self.sys.getTrackedDeviceIndexForControllerRole(h["role"])
                if d == openvr.k_unTrackedDeviceIndexInvalid or not self.sys.isTrackedDeviceConnected(d):
                    h.update(armed=False, held=False, device=None)
                    continue
                if d != h["device"]:
                    h.update(armed=False, held=False, device=d)
                model = self.sys.getStringTrackedDeviceProperty(d, openvr.Prop_RenderModelName_String)
                mode = openvr.RenderModel_ControllerMode_State_t()
                ok1, cur = self.rm.getComponentStateForDevicePath(model, "button_grip", h["path"], mode)
                ok2, rest = self.rm.getComponentState(model, "button_grip", openvr.VRControllerState_t(), mode)
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
            out.append((d, held, held and not h["held"]))
            h["held"] = held
        return out


class OverlayHost:
    def __init__(self, pad, config):
        self.pad = pad
        self.config = config            # dict persisted by the pad (pos/scale/pinned/...)
        openvr.init(openvr.VRApplication_Overlay)
        self.ov = openvr.VROverlay()
        self.system = openvr.VRSystem()
        # Two overlays, double-buffered: a new image loads into the hidden one, which is shown
        # before the old one is hidden. Reloading the visible overlay blanked it for a frame or
        # two (flicker on every hover change).
        self.handles = [self.ov.createOverlay(KEY, "Arrow Pad"),
                        self.ov.createOverlay(KEY + ".b", "Arrow Pad")]
        self.front = 0                  # index of the overlay being shown
        self.width_m = float(config.get("width_m", WIDTH_DEFAULT))
        # Only the overlay on top takes laser input; the other is set to None until it swaps in.
        # (Both took input at first, so for ~50 ms per redraw a click reached both overlays and
        # counted twice: a single tap locked a modifier or toggled R/M twice.)
        for i, h in enumerate(self.handles):
            self.ov.setOverlayInputMethod(h, openvr.VROverlayInputMethod_Mouse if i == 0
                                          else openvr.VROverlayInputMethod_None)
            self.ov.setOverlaySortOrder(h, 10)
            self.ov.setOverlayWidthInMeters(h, self.width_m)
            # One pointer per laser, like Full Keyboard: hold a modifier with one hand and press a
            # key with the other. Events then say which laser (cursorIndex) they came from.
            self.ov.setOverlayFlag(h, openvr.VROverlayFlags_MultiCursor, True)
        self.last_button_time = {}             # event type -> time: drops a click seen twice
        self.image_hash = None          # last uploaded image, to skip identical uploads
        self.sizes = [(0, 0), (0, 0)]   # mouse scale per overlay
        self.hover = None               # button under the laser
        self.pressed = {}               # laser (cursor index) -> button it's pressing
        self.hovered_devices = set()    # controllers whose laser is on the pad
        self.grip_drag = False          # the current drag is a grip squeeze (ends on release)
        try:
            self.grips = GripReader()
        except Exception:
            self.grips = None
        self.drag = None                # (device, offset, controller start, depth axis) while dragging
        self.last_device = None         # controller behind the latest laser event
        self.last_render = 0.0
        self.ticks = 0
        self._dash = False
        self.tex_slot = 0
        self.dirty = True
        self.swapping = False
        self.offset = config.get("vr_offset")       # pose relative to the dashboard anchor
        self.pose = None
        if not (self.offset and self.follow_dashboard()) or self.distance_from_head() > MAX_DISTANCE:
            self.reset_position()
        self.visible = False
        QTimer(pad, interval=22, timeout=self.poll).start()      # ~45 Hz event pump
        QTimer(pad, interval=100, timeout=self.mark_dirty).start()   # state changes (mic etc.)

    # ---- rendering ------------------------------------------------------
    def mark_dirty(self):
        """Periodic check: redraw only when something visible changed (mic colour, modifiers,
        layer, pin, language), so SteamVR doesn't reload the image for nothing."""
        p = self.pad
        sig = (p.layer, tuple(p.mod_state.values()), p.dictation_state(), p.pinned, p.lang, p.scale,
               p.click_swap.armed)
        if sig != getattr(self, "_sig", None):
            self._sig = sig
            self.dirty = True

    @property
    def handle(self):
        return self.handles[self.front]

    @property
    def size(self):
        """Widget pixel size of the image shown (the overlays' mouse scale)."""
        return self.sizes[self.front] if self.sizes[self.front][0] else self.sizes[self.front ^ 1]

    def render(self):
        now = time.monotonic()
        if now - self.last_render < MIN_RENDER_INTERVAL or self.swapping:
            return                                   # stays dirty; drawn on a later tick
        self.dirty = False
        img = self.pad.grab().toImage()
        digest = hashlib.blake2b(img.constBits().asstring(img.sizeInBytes()), digest_size=16).digest()
        if digest == self.image_hash:
            return                                   # looks the same: nothing to upload
        self.image_hash = digest
        self.last_render = now
        w, h = img.width(), img.height()       # widget pixels: laser coordinates use these
        if img.width() > MAX_TEX[0] or img.height() > MAX_TEX[1]:
            img = img.scaled(MAX_TEX[0], MAX_TEX[1], Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        # Alternate between two files so SteamVR reloads the image each time.
        self.tex_slot ^= 1
        path = f"{TEX_DIR}/arrowpad-overlay-{self.tex_slot}.png"
        # Light compression: half the encode time (~7 ms instead of ~15); the file lives in RAM
        # (/run), so its larger size costs nothing. A direct GPU texture, as Full Keyboard uses,
        # would need an OpenGL context, which here only exists through Gamescope's WSI layer.
        img.save(path, "PNG", 90)
        back = self.front ^ 1
        self.ov.setOverlayFromFile(self.handles[back], path)
        if (w, h) != self.sizes[back]:
            self.sizes[back] = (w, h)
            scale = openvr.HmdVector2_t()
            scale.v[0], scale.v[1] = w, h
            self.ov.setOverlayMouseScale(self.handles[back], scale)
        if self.visible:
            self.swapping = True
            QTimer.singleShot(SWAP_SHOW_MS, self.swap)   # give SteamVR time to load it
        else:
            self.set_input(back)
            self.front = back

    def set_input(self, front):
        """Laser input goes to `front` only."""
        for i, h in enumerate(self.handles):
            self.ov.setOverlayInputMethod(h, openvr.VROverlayInputMethod_Mouse if i == front
                                          else openvr.VROverlayInputMethod_None)

    def swap(self):
        """Show the freshly loaded overlay on top, then hide the old one. Input moves to the new
        one at the same moment, so a click never reaches both."""
        old, new = self.front, self.front ^ 1
        self.set_input(new)
        self.front = new
        if self.visible:
            self.ov.setOverlaySortOrder(self.handles[new], 11)
            self.ov.setOverlaySortOrder(self.handles[old], 10)
            self.ov.showOverlay(self.handles[new])
            QTimer.singleShot(SWAP_HIDE_MS, lambda: self.front != old and self.ov.hideOverlay(self.handles[old]))
        self.swapping = False

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
        # The anchor's reported pose wobbles slightly; moving on every wobble looked like shimmer.
        if not self.pose or max(abs(a - b) for ra, rb in zip(pose, self.pose) for a, b in zip(ra, rb)) > POSE_EPSILON:
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
        m = _mat(self.pose)
        for h in self.handles:
            self.ov.setOverlayTransformAbsolute(h, openvr.TrackingUniverseStanding, m)

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
        for h in self.handles:
            self.ov.setOverlayWidthInMeters(h, self.width_m)
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
        self.ticks += 1
        if self.ticks % 9 == 1:                 # dashboard open? ~5x a second is plenty
            self._dash = bool(self.ov.isDashboardVisible())
        visible = self._dash
        if visible != self.visible:
            if visible:
                self.ov.showOverlay(self.handle)
            else:
                for h in self.handles:
                    self.ov.hideOverlay(h)
                # Like Full Keyboard: closing the dashboard releases our input (a pending
                # right/middle-click toggle would otherwise change a click you can't see coming).
                self.hovered_devices.clear()
                if self.drag is not None:
                    self.end_drag()
                if self.pad.click_swap.armed:
                    self.pad.click_swap.disarm("dashboard closed")
                # ...and lets go of held modifiers: a locked Super or Ctrl would otherwise turn
                # every click you make with the dashboard closed into Super/Ctrl+click.
                self.pad.release_all_mods()
                self.pad.restyle()
            self.visible = visible
        grips = self.grips.poll() if (self.grips and visible) else []
        self.gripping = {d for d, held, _ in grips if held}
        for d, held, pressed in grips:
            # Squeeze while that controller's laser is on the pad: grab it (keys included).
            if pressed and d in self.hovered_devices and self.drag is None and not self.pad.pinned:
                self.start_drag(d, grip=True)
        if self.drag is not None and self.grip_drag and self.drag[0] not in self.gripping:
            self.end_drag()
        if self.drag is not None:
            self.drag_follow()                  # every tick, not just on laser moves
        elif visible and self.ticks % 5 == 0:
            self.follow_dashboard()             # ride along with the dashboard, ~10x a second
        for handle in self.handles:
            self.pump(handle)
        if self.dirty and visible:
            self.render()

    INPUT_LOG = f"{TEX_DIR}/arrowpad-input.log"

    def log_input(self, msg):
        """Presses and releases as SteamVR reports them and where they land (for diagnosis)."""
        try:
            if os.path.exists(self.INPUT_LOG) and os.path.getsize(self.INPUT_LOG) > 200_000:
                os.replace(self.INPUT_LOG, self.INPUT_LOG + ".1")
            with open(self.INPUT_LOG, "a") as f:
                f.write(f"{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d} {msg}\n")
        except OSError:
            pass

    def describe(self, w):
        if w is None:
            return "nothing"
        for r, c, b in self.pad.buttons:
            if b is w:
                return f"key {self.pad.name_at(r, c)!r} (row {r}, col {c})"
        for name, b in self.pad.tools.items():
            if b is w:
                return f"tool {name!r}"
        return f"{type(w).__name__} {w.text()!r}"

    def pump(self, handle):
        ev = openvr.VREvent_t()
        # pyopenvr returns (result, event): test the result, or this loops forever.
        while self.ov.pollNextOverlayEvent(handle, ev)[0]:
            t, dev = ev.eventType, ev.trackedDeviceIndex
            cursor = ev.data.mouse.cursorIndex if t in (
                openvr.VREvent_MouseMove, openvr.VREvent_MouseButtonDown, openvr.VREvent_MouseButtonUp) else 0
            if t in (openvr.VREvent_MouseButtonDown, openvr.VREvent_MouseButtonUp):
                m = ev.data.mouse
                self.log_input(f"{'down' if t == openvr.VREvent_MouseButtonDown else 'up  '} overlay "
                               f"{self.handles.index(handle) if handle in self.handles else '?'} (front "
                               f"{self.front}) laser {cursor} device {dev} raw ({m.x:.1f}, {m.y:.1f}) "
                               f"size {self.size} -> {self.to_widget(m).x()},{self.to_widget(m).y()} "
                               f"on {self.describe(self.button_at(self.to_widget(m)))}")
                # Backstop: a press (or release) of the same laser within 60 ms of the previous
                # one is the same click seen by the other overlay. Real taps are far slower.
                now = time.monotonic()
                if now - self.last_button_time.get((t, cursor), -1.0) < 0.06:
                    continue
                self.last_button_time[(t, cursor)] = now
            if t == openvr.VREvent_FocusLeave:
                if dev == openvr.k_unTrackedDeviceIndexInvalid:
                    self.hovered_devices.clear()
                else:
                    self.hovered_devices.discard(dev)
                continue
            self.last_device = dev
            if t == openvr.VREvent_MouseMove:
                pos = self.to_widget(ev.data.mouse)
                self.hovered_devices.add(dev)
                if self.drag is not None:
                    self.drag_follow()
                else:
                    self.set_hover(self.button_at(pos), dev)
                    if cursor in self.pressed:
                        self.send(self.pressed[cursor], QEvent.Type.MouseMove, pos, Qt.MouseButton.LeftButton)
            elif t == openvr.VREvent_MouseButtonDown:
                pos = self.to_widget(ev.data.mouse)
                b = self.button_at(pos)
                if dev in getattr(self, "gripping", ()) or self.drag is not None:
                    continue                    # squeezing to grab: a trigger pull doesn't also type
                if b is not None:
                    self.pressed[cursor] = b
                    self.send(b, QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton)
                    self.dirty = True
                elif not self.pad.pinned:
                    # Trigger on the background also grabs (until the trigger is released).
                    self.start_drag(dev, grip=False)
            elif t == openvr.VREvent_MouseButtonUp:
                pos = self.to_widget(ev.data.mouse)
                b = self.pressed.pop(cursor, None)
                if b is not None:
                    self.send(b, QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.NoButton)
                    self.dirty = True
                if self.drag is not None and not self.grip_drag and self.drag[0] == dev:
                    self.end_drag()

    def start_drag(self, dev, grip):
        """Grab: the panel follows the controller rigidly, like Full Keyboard's grab. (Moving it
        by laser coordinates on the panel ran away.)"""
        ctrl = self.device_matrix(dev)
        if ctrl is None:
            return
        for c, b in list(self.pressed.items()):        # a grab cancels presses in progress
            self.send(b, QEvent.Type.MouseButtonRelease, QPoint(-1, -1), Qt.MouseButton.NoButton)
        self.pressed.clear()
        self.grip_drag = grip
        self.drag = (dev, _rigid_mul(_rigid_inv(ctrl), self.pose),
                     [ctrl[r][3] for r in range(3)], self.depth_axis())

    def end_drag(self):
        self.drag, self.grip_drag = None, False
        if self.distance_from_head() > MAX_DISTANCE:
            self.reset_position()
        else:
            self.remember_offset()     # the new spot, relative to the dashboard
            self.ease_level()
        self.save()

    # ---- after a grab: ease a slight sideways lean level (Full Keyboard does this) -----------
    LEVEL_MAX_DEG, LEVEL_MS, LEVEL_STEPS = 5.0, 500, 20

    def roll(self):
        """Sideways lean in radians, measured in the pad's own plane: turning the pad about its
        normal by this angle (rotate_about_normal) makes its left-right edge horizontal."""
        return math.atan2(self.pose[1][0], self.pose[1][1])

    def ease_level(self):
        """A lean under 5° eases level over 500 ms, keeping the forward tilt; bigger ones stay."""
        if not self.pose:
            return
        r = self.roll()
        if abs(r) < 1e-3 or abs(math.degrees(r)) > self.LEVEL_MAX_DEG:
            return
        step = r / self.LEVEL_STEPS
        self._level_left = self.LEVEL_STEPS

        def tick():
            if self.drag is not None or self._level_left <= 0 or not self.pose:
                timer.stop()
                return
            self.rotate_about_normal(step)
            self._level_left -= 1
            if self._level_left == 0:
                timer.stop()
                self.remember_offset()
                self.save()

        timer = QTimer(self.pad, interval=self.LEVEL_MS // self.LEVEL_STEPS, timeout=tick)
        timer.start()
        self._level_timer = timer

    def rotate_about_normal(self, angle):
        """Turn the pad in its own plane (about its normal, the z column) by `angle` radians."""
        x = [self.pose[i][0] for i in range(3)]
        y = [self.pose[i][1] for i in range(3)]
        c, s_ = math.cos(angle), math.sin(angle)
        for i in range(3):
            self.pose[i][0] = c * x[i] - s_ * y[i]
            self.pose[i][1] = s_ * x[i] + c * y[i]
        self.apply_pose()

    def depth_axis(self):
        """Horizontal unit vector from the head toward the pad (the push/pull direction)."""
        head = self.device_matrix(openvr.k_unTrackedDeviceIndex_Hmd)
        if head is None or not self.pose:
            return None
        v = [self.pose[0][3] - head[0][3], 0.0, self.pose[2][3] - head[2][3]]
        n = math.hypot(v[0], v[2])
        return [v[0] / n, 0.0, v[2] / n] if n > 1e-3 else None

    def drag_follow(self):
        """While grabbed: overlay = controller now x (controller at grab)^-1 x overlay at grab,
        and the controller's push/pull along the head-to-pad direction is amplified
        (DEPTH_GAIN), so the pad can be sent far away or brought close without walking."""
        dev, offset, start, axis = self.drag
        ctrl = self.device_matrix(dev)
        if ctrl is None:
            return
        pose = _rigid_mul(ctrl, offset)
        head = self.device_matrix(openvr.k_unTrackedDeviceIndex_Hmd)
        if axis is not None and head is not None:
            pushed = sum((ctrl[i][3] - start[i]) * axis[i] for i in range(3))
            extra = pushed * (DEPTH_GAIN - 1)
            # keep it between DEPTH_MIN and DEPTH_MAX from the head, measured along the axis
            dist = sum((pose[i][3] - head[i][3]) * axis[i] for i in range(3))
            extra = min(max(extra, DEPTH_MIN - dist), DEPTH_MAX - dist)
            for i in range(3):
                pose[i][3] += axis[i] * extra
        self.pose = pose
        self.apply_pose()

    def close(self):
        try:
            for h in self.handles:
                self.ov.destroyOverlay(h)
            openvr.shutdown()       # disconnect cleanly (exiting while connected can crash)
        except Exception:
            pass

    def dump(self):
        return json.dumps({"width_m": self.width_m})
