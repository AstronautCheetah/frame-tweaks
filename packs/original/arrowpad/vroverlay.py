"""Arrow Pad as a native SteamVR overlay (VR mode), the way Full Keyboard works.

A floating *window* takes keyboard focus when you click it in VR (gamescope ignores the
"don't focus me" hint and won't hand focus back), so its keys went to itself. An overlay never
takes focus: the pad is drawn off-screen, shown as an overlay texture, and the SteamVR laser's
mouse events are fed back into its buttons. Keys then reach the app you were using, and
haptics go to the controller that's pointing (an overlay being pointed at has input focus).

Like Full Keyboard: visible while the dashboard is, Reset puts it in front of you, +/- change
its width in 5 cm steps (0.30–2 m), drag the panel to move it, Pin stops that.
"""
import glob
import hashlib
import math
import os
import time

import ftconf  # noqa: E402  (beside i18n.py: arrowpad.py puts that folder on sys.path)
import openvr
import vrkit  # noqa: E402
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PyQt6.QtGui import QImage, QMouseEvent
from PyQt6.QtWidgets import QApplication, QPushButton

KEY = "frame-tweaks.arrowpad"
# The texture goes to SteamVR as a PNG file (SetOverlayFromFile), not SetOverlayRaw: on the Frame
# raw uploads never showed (an invisible panel that still caught the laser), and a 2.5 MB raw
# upload crashed vrcompositor (SIGBUS). Capped size and rate keep the compositor's work small.
MAX_TEX = (1024, 768)
MIN_RENDER_INTERVAL = 0.15           # at most ~7 texture updates a second
COVER_MS = 120                       # how long the cover hides a reload (the blink is shorter)
DEPTH_GAIN = 3.0                     # dragging: push/pull moves the pad 3x as far; up/down/sideways 1:1
DEPTH_MIN, DEPTH_MAX = 0.25, 3.5     # dragging: keep the pad this far from your head (m, horizontally)
POSE_EPSILON = 0.0015                # ignore anchor jitter below 1.5 mm (and ~0.1°)
TEX_DIR = f"/run/user/{os.getuid()}"
MAX_DISTANCE = 4.0       # metres from the headset; further than that, bring it back
WIDTH_DEFAULT, WIDTH_MIN, WIDTH_MAX, WIDTH_STEP = 0.55, 0.30, 2.0, 0.05
# Placement like Full Keyboard: anchored to Steam's dashboard (its main panel while visible, else
# the dashboard bar), top edge 6 cm below its bottom centre, 24 cm toward you, tilted back 50°.
# The pad keeps that offset *relative to the dashboard bar*, so it follows the dashboard around
# (recentering, moving it, a re-centred play space), as Full Keyboard does. It follows the bar,
# not the main panel: the main panel is hidden while the Desktop tab is showing, so following
# "main if visible, else bar" made the pad jump each time you switched between Steam and Desktop.
DASHBOARD_MAIN, DASHBOARD_BAR = "valve.steam.gamepadui.main", "valve.steam.gamepadui.bar"
FOLLOW = (DASHBOARD_BAR, DASHBOARD_MAIN)       # what the pad rides along with
PLACE = (DASHBOARD_MAIN, DASHBOARD_BAR)        # what Reset puts it beneath
GAP_BELOW, TOWARD_VIEWER, PITCH_DEG = 0.06, 0.24, 50
FORWARD, BELOW = 0.55, 0.30          # fallback without a dashboard: in front of the headset


class OverlayHost:
    def __init__(self, pad, config):
        self.pad = pad
        self.config = config            # dict persisted by the pad (pos/scale/pinned/...)
        openvr.init(openvr.VRApplication_Overlay)
        self.ov = openvr.VROverlay()
        self.system = openvr.VRSystem()
        # ONE overlay, set up once: input mode, sort order and flags never change afterwards.
        # (Two double-buffered overlays avoided reload flicker, but swapping them made SteamVR
        # deliver a held press again to the newly shown one, so taps counted twice; switching
        # their input modes on the fly crashed SteamVR's client inside PollNextOverlayEvent, and
        # a separate transparent input overlay got no laser input at all.) Flicker is kept down
        # by redrawing only when something really changes (see set_hover / mark_dirty), and the
        # reload that remains is hidden behind the cover overlay (see render).
        self.input_handle = self.ov.createOverlay(KEY, "Arrow Pad")
        self.handles = [self.input_handle]
        self.front = 0
        self.width_m = float(config.get("width_m", WIDTH_DEFAULT))
        self.ov.setOverlayInputMethod(self.input_handle, openvr.VROverlayInputMethod_Mouse)
        self.ov.setOverlaySortOrder(self.input_handle, 10)
        self.ov.setOverlayWidthInMeters(self.input_handle, self.width_m)
        # One pointer per laser, like Full Keyboard: hold a modifier with one hand and press a key
        # with the other. Events then say which laser (cursorIndex) they came from.
        self.ov.setOverlayFlag(self.input_handle, openvr.VROverlayFlags_MultiCursor, True)
        self.input_size = (0, 0)        # widget pixels the mouse scale is set to
        # The cover: display only (no input method, so it never takes laser input), drawn above
        # the pad and holding the previous image. While the pad reloads a new image, which
        # blinks, the cover shows the old one on top; then it steps aside and loads the new one
        # out of sight, ready for the next change.
        try:
            self.cover = self.ov.createOverlay(KEY + ".cover", "Arrow Pad")
            self.ov.setOverlaySortOrder(self.cover, 11)
            self.ov.setOverlayWidthInMeters(self.cover, self.width_m)
        except Exception:
            self.cover = None
        self.cover_path = None          # image the cover holds (None until its first load)
        self.last_button_time = {}             # event type -> time: drops a click seen twice
        self.image_hash = None          # last uploaded image, to skip identical uploads
        self.hover = None               # button under the laser
        self.pressed = {}               # laser (cursor index) -> button it's pressing
        self.hovered_devices = set()    # controllers whose laser is on the pad
        self.grip_drag = False          # the current drag is a grip squeeze (ends on release)
        try:
            self.grips = vrkit.GripReader(openvr)
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
        self.offset = config.get("vr_offset")       # pose relative to the dashboard bar
        self.pose = None
        if self.offset and config.get("vr_anchor") != "bar":
            # Saved by an older version, relative to the main panel whenever it was showing.
            old = self.dashboard_anchor(PLACE)
            if old is not None:
                self.pose = vrkit.rigid_mul(old, self.offset)
                self.remember_offset()
                self.pose = None
        if not (self.offset and self.follow_dashboard()) or self.distance_from_head() > MAX_DISTANCE:
            self.reset_position()
        self.visible = False
        QTimer(pad, interval=22, timeout=self.poll).start()      # ~45 Hz event pump
        QTimer(pad, interval=100, timeout=self.mark_dirty).start()   # state changes (mic etc.)

    # ---- rendering ------------------------------------------------------
    def uncover(self, path):
        """The pad shows the new image now: hide the cover and load that image into it."""
        if getattr(self, "closed", False):
            return                  # (a timer due with the Close that disconnected: no SteamVR now)
        try:
            self.ov.hideOverlay(self.cover)
            self.ov.setOverlayFromFile(self.cover, path)
            self.cover_path = path
        except Exception:
            pass
        self.swapping = False

    def mark_dirty(self):
        """Periodic check: redraw only when something visible changed (mic colour, modifiers,
        layer, pin, language), so SteamVR doesn't reload the image for nothing."""
        p = self.pad
        sig = (p.layer, tuple(p.mod_state.values()), p.dictation_state(), p.pinned, p.lang, p.scale,
               p.click_swap.armed, p.settings_page.isVisible(), p.haptic_level, p.cfg.get("theme"), p.collapsed)
        if sig != getattr(self, "_sig", None):
            self._sig = sig
            # Colour the buttons for this state *before* the redraw: the pad's own mic refresh
            # runs on a slower timer, and a redraw that beat it showed the previous colour (no
            # red on the first tap, yellow left behind after the text arrived).
            p.restyle()
            self.dirty = True

    @property
    def size(self):
        """Widget pixel size of the pad: the input overlay's mouse scale."""
        return self.input_size

    def set_input_size(self, w, h):
        """Mouse coordinates in widget pixels."""
        if (w, h) == self.input_size:
            return
        scale = openvr.HmdVector2_t()
        scale.v[0], scale.v[1] = w, h
        self.ov.setOverlayMouseScale(self.input_handle, scale)
        self.input_size = (w, h)

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
        resized = self.fit_size(w, h)
        if img.width() > MAX_TEX[0] or img.height() > MAX_TEX[1]:
            img = img.scaled(MAX_TEX[0], MAX_TEX[1], Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        # A new file name for every image: SteamVR caches overlay images by path, so reusing a
        # name (this used to alternate between two fixed names) could keep showing an image an
        # older pad wrote there, even after reinstalling. Older files are deleted.
        self.tex_slot += 1
        path = f"{TEX_DIR}/arrowpad-overlay-{os.getpid()}-{self.tex_slot}.png"
        # Normal compression (~35 KB): SteamVR loads a small file faster, so the panel's blink on
        # reload is shorter; our ~15 ms to encode is the cheaper side. (A direct GPU texture, as
        # Full Keyboard uses, needs an OpenGL context, which here only exists through Gamescope's
        # WSI layer.)
        img.save(path, "PNG")
        covered = self.cover is not None and self.cover_path is not None and not resized   # (old size: no cover)
        if covered:
            self.ov.showOverlay(self.cover)          # old image on top while the pad reloads
            self.swapping = True
        self.ov.setOverlayFromFile(self.input_handle, path)
        self.set_input_size(w, h)
        if self.cover is not None:
            QTimer.singleShot(COVER_MS if covered else 0, lambda: self.uncover(path))
        for old in glob.glob(f"{TEX_DIR}/arrowpad-overlay-*.png"):
            if old not in (path, getattr(self, "_last_path", None), self.cover_path):
                try:
                    os.remove(old)
                except OSError:
                    pass
        self._last_path = path

    def fit_size(self, w, h):
        """The panel's width follows the picture's (Collapse shows just the chevron): metres per
        pixel as the expanded pad has them. On Collapse / Expand the chevron's point stays where
        it was, under the laser (as Screen snip's panel does). True if the size changed."""
        k = self.width_m / (self.pad.expanded_size.width() or w)
        last = getattr(self, "last_px", None)
        if abs(w * k - getattr(self, "shown_width", self.width_m)) > 1e-4:
            self.shown_width = w * k
            self.ov.setOverlayWidthInMeters(self.input_handle, self.shown_width)
            if self.cover is not None:
                self.ov.setOverlayWidthInMeters(self.cover, self.shown_width)
        old_pv, pv = getattr(self, "last_pivot", None), self.pad.pivot()
        resized = last is not None and last != (w, h)
        if resized and self.pad.toggled and self.pose and old_pv is not None:
            old_w, old_h = last
            a = (old_pv.x() - old_w / 2 - (pv.x() - w / 2)) * k     # along the panel's x
            b = (old_pv.y() - old_h / 2 - (pv.y() - h / 2)) * k     # pixels down = -y
            self.pose = [[c[0], c[1], c[2], c[3] + c[0] * a - c[1] * b] for c in self.pose]
            self.log_input(f"fold: {last} -> {(w, h)}, chevron {old_pv.x()},{old_pv.y()} -> {pv.x()},{pv.y()} px, "
                           f"panel moved {a:+.3f} m across, {-b:+.3f} m up")
            self.apply_pose()
            self.remember_offset()
            self.save()
        self.pad.toggled = False
        self.last_px, self.last_pivot = (w, h), pv
        return resized

    # ---- placement --------------------------------------------------------
    def device_matrix(self, index):
        poses = self.system.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0,
                                                            openvr.k_unMaxTrackedDeviceCount)
        if index is None or index >= len(poses) or not poses[index].bPoseIsValid:
            return None
        m = poses[index].mDeviceToAbsoluteTracking.m
        return [[m[r][c] for c in range(4)] for r in range(3)]

    def dashboard_anchor(self, keys=FOLLOW):
        """Bottom centre of the first available dashboard part in keys (the main panel counts
        only while visible) as a rigid 3x4 transform with its scale removed; None if none is."""
        for key in keys:
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
        pose = vrkit.rigid_mul(anchor, self.offset)
        # The anchor's reported pose wobbles slightly; moving on every wobble looked like shimmer.
        if not self.pose or max(abs(a - b) for ra, rb in zip(pose, self.pose) for a, b in zip(ra, rb)) > POSE_EPSILON:
            self.pose = pose
            self.apply_pose()
        return True

    def remember_offset(self):
        anchor = self.dashboard_anchor()
        if anchor is not None and self.pose:
            self.offset = vrkit.relative(anchor, self.pose)

    def distance_from_head(self):
        head = self.device_matrix(openvr.k_unTrackedDeviceIndex_Hmd)
        if head is None or not self.pose:
            return 0.0
        return math.dist([head[r][3] for r in range(3)], [self.pose[r][3] for r in range(3)])

    def apply_pose(self):
        m = vrkit.hmd34(openvr, self.pose)
        self.ov.setOverlayTransformAbsolute(self.input_handle, openvr.TrackingUniverseStanding, m)
        if getattr(self, "cover", None) is not None:
            self.ov.setOverlayTransformAbsolute(self.cover, openvr.TrackingUniverseStanding, m)

    def reset_position(self):
        """Beneath the dashboard like Full Keyboard (or in front of the headset without one)."""
        anchor = self.dashboard_anchor(PLACE)
        # The panel's height as shown, collapsed too (metres per pixel as fit_size has them).
        w, h = self.size
        h_m = h * self.width_m / (self.pad.expanded_size.width() or w) if w else 0.8 * self.width_m
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
            az, ay, ax = [-fx, 0.0, -fz], [0.0, 1.0, 0.0], [-fz, 0.0, fx]     # x = forward x up: your right
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
        self.shown_width = self.width_m                    # (only while expanded: +/- hide when collapsed)
        self.ov.setOverlayWidthInMeters(self.input_handle, self.width_m)
        if self.cover is not None:
            self.ov.setOverlayWidthInMeters(self.cover, self.width_m)
        self.save()

    def step_width(self, steps):
        self.set_width(self.width_m + steps * WIDTH_STEP)

    def save(self):
        self.config["width_m"] = self.width_m
        self.config["vr_offset"] = self.offset
        self.config["vr_anchor"] = "bar"
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
            try:
                self.hover.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
                QApplication.sendEvent(self.hover, QEvent(QEvent.Type.Leave))
                self.hover.update()
            except RuntimeError:        # (deleted: a language change rebuilds the settings page)
                pass
        self.hover = button
        if button is not None:
            button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, True)
            QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))   # hover haptic filter
            if button.property("tool") != "true":
                self.pad.pulse("hover", device)
        # No redraw for hover: every reload of the single overlay can blink, so the image only
        # changes on presses and state changes; hovering is felt (haptic tick), not drawn.

    def poll(self):
        if getattr(self, "closed", False):
            return
        self.ticks += 1
        if self.ticks % 9 == 1:                 # dashboard open? ~5x a second is plenty
            self._dash = bool(self.ov.isDashboardVisible())
        visible = self._dash
        if visible != self.visible:
            if visible:
                self.ov.showOverlay(self.input_handle)
            else:
                self.ov.hideOverlay(self.input_handle)
                if self.cover is not None:
                    self.ov.hideOverlay(self.cover)
                # Like Full Keyboard: closing the dashboard releases our input (a pending
                # right/middle-click toggle would otherwise change a click you can't see coming).
                self.hovered_devices.clear()
                # ...and the keys lasers hold down: a release may never reach the hidden panel (the
                # key would repeat on), and one arriving later would latch a modifier again.
                self.cancel_presses()
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
        self.pump(self.input_handle)            # the only overlay that takes laser input
        if self.dirty and visible and not getattr(self, "closed", False):   # (Close in pump: disconnected)
            self.render()

    INPUT_LOG = f"{TEX_DIR}/arrowpad-input.log"

    def log_input(self, msg):
        """Presses and releases as SteamVR reports them and where they land (for diagnosis)."""
        ftconf.append_log(self.INPUT_LOG, msg, stamp="%H:%M:%S.ms")

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
        while not getattr(self, "closed", False) and self.ov.pollNextOverlayEvent(handle, ev)[0]:
            t, dev = ev.eventType, ev.trackedDeviceIndex
            cursor = ev.data.mouse.cursorIndex if t in (
                openvr.VREvent_MouseMove, openvr.VREvent_MouseButtonDown, openvr.VREvent_MouseButtonUp) else 0
            if t in (openvr.VREvent_MouseButtonDown, openvr.VREvent_MouseButtonUp):
                try:                            # diagnostics must never break input handling
                    m = ev.data.mouse
                    handles = getattr(self, "handles", [])
                    pos = self.to_widget(m)
                    self.log_input(f"{'down' if t == openvr.VREvent_MouseButtonDown else 'up  '} overlay "
                                   f"{handles.index(handle) if handle in handles else '?'} (front "
                                   f"{self.front}) laser {cursor} device {dev} raw ({m.x:.1f}, {m.y:.1f}) "
                                   f"size {self.size} -> {pos.x()},{pos.y()} on {self.describe(self.button_at(pos))}")
                except Exception:
                    pass
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
                    # No redraw for the press itself: each reload of the overlay blinks, and the
                    # press is felt (haptic click). State changes (modifiers, layer, R/M, mic, pin,
                    # settings) still redraw through mark_dirty.
                    self.send(b, QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton)
                elif not self.pad.pinned:
                    # Trigger on the background also grabs (until the trigger is released).
                    self.start_drag(dev, grip=False)
            elif t == openvr.VREvent_MouseButtonUp:
                pos = self.to_widget(ev.data.mouse)
                b = self.pressed.pop(cursor, None)
                if b is not None:
                    self.send(b, QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.NoButton)
                if self.drag is not None and not self.grip_drag and self.drag[0] == dev:
                    self.end_drag()

    def cancel_presses(self):
        """Take back the presses lasers hold (a grab, the dashboard closing, Close): a release off
        the key, so nothing is clicked, and the pad lets go of what each holds down (that release
        alone left a held ↓ or Bksp down, repeating in your app)."""
        for b in list(self.pressed.values()):
            self.send(b, QEvent.Type.MouseButtonRelease, QPoint(-1, -1), Qt.MouseButton.NoButton)
            self.pad.let_go(b)
        self.pressed.clear()

    def start_drag(self, dev, grip):
        """Grab: the panel follows the controller rigidly, like Full Keyboard's grab. (Moving it
        by laser coordinates on the panel ran away.)"""
        ctrl = self.device_matrix(dev)
        if ctrl is None:
            return
        self.cancel_presses()                       # a grab cancels presses in progress
        self.grip_drag = grip
        self.drag = (dev, vrkit.relative(ctrl, self.pose),
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
            if self.drag is not None or self._level_left <= 0 or not self.pose or getattr(self, "closed", False):
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
        pose = vrkit.rigid_mul(ctrl, offset)
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
        """Disconnect from SteamVR. Close is pressed from inside pump(): no more events are read
        after this (reading them from a closed connection crashed the pad on Close)."""
        if getattr(self, "closed", False):
            return
        self.cancel_presses()       # (a key the other laser holds would stay down after we exit)
        self.closed = True
        try:
            self.ov.destroyOverlay(self.input_handle)
            if self.cover is not None:
                self.ov.destroyOverlay(self.cover)
            openvr.shutdown()       # disconnect cleanly (exiting while connected can crash)
        except Exception:
            pass
