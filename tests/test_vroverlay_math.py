"""Arrow Pad VR overlay geometry: easing a slight sideways lean level after a grab."""
import math
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402


def load():
    # vroverlay imports openvr and Qt at the top; the geometry needs neither.
    fake = {"openvr": types.ModuleType("openvr"), "PyQt6": types.ModuleType("PyQt6")}
    for m, names in {"QtCore": ("QEvent", "QPoint", "QPointF", "Qt", "QTimer"),
                     "QtGui": ("QImage", "QMouseEvent"), "QtWidgets": ("QApplication", "QPushButton")}.items():
        mod = types.ModuleType("PyQt6." + m)
        for n in names:
            setattr(mod, n, object)
        fake["PyQt6." + m] = mod
    with mock.patch.dict(sys.modules, fake):
        v = load_script(ROOT / "packs/original/arrowpad" / "vroverlay.py", "vroverlay")
    return v


class Level(unittest.TestCase):
    def test_lean_eases_to_level_keeping_tilt(self):
        v = load()
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.apply_pose = lambda: None
        p = math.radians(50)
        x, y, z = [1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]
        for lean in (4, -3, 0.5):
            o.pose = [[x[i], y[i], z[i], 0.0] for i in range(3)]
            o.rotate_about_normal(math.radians(lean))
            r = o.roll()
            self.assertAlmostEqual(abs(math.degrees(r)), abs(lean), places=6)
            for _ in range(o.LEVEL_STEPS):
                o.rotate_about_normal(r / o.LEVEL_STEPS)
            self.assertAlmostEqual(o.pose[1][0], 0.0, places=9)          # left-right edge level
            for i in range(3):
                self.assertAlmostEqual(o.pose[i][2], z[i], places=9)     # same normal: tilt kept


class DoubleClick(unittest.TestCase):
    def test_click_reaching_both_overlays_counts_once(self):
        v = load()
        ov = types.SimpleNamespace(
            VREvent_MouseMove=300, VREvent_MouseButtonDown=301, VREvent_MouseButtonUp=302)

        class Ev:
            def __init__(self):
                self.eventType = 0
                self.trackedDeviceIndex = 1
                self.data = types.SimpleNamespace(mouse=types.SimpleNamespace(x=10, y=10, cursorIndex=0))
        v.openvr.VREvent_t = Ev
        for k in ("VREvent_MouseMove", "VREvent_MouseButtonDown", "VREvent_MouseButtonUp"):
            setattr(v.openvr, k, getattr(ov, k))
        v.openvr.VREvent_FocusLeave, v.openvr.k_unTrackedDeviceIndexInvalid = 304, 2 ** 32 - 1
        queues = {"A": [301, 302], "B": [301, 302]}      # one physical click, seen by both

        def poll(handle, ev):
            if queues[handle]:
                ev.eventType = queues[handle].pop(0)
                return (True, ev)
            return (False, ev)
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.ov = types.SimpleNamespace(pollNextOverlayEvent=poll)
        o.last_button_time, o.pressed, o.drag, o.dirty = {}, {}, None, False
        o.hovered_devices, o.grip_drag = set(), False
        o.input_size, o.front = (100, 100), 0
        o.pad = types.SimpleNamespace(pinned=True)
        sent = []
        o.button_at = lambda pos: "Super"
        o.send = lambda w, etype, pos, buttons: sent.append(etype)
        v.QEvent = types.SimpleNamespace(Type=types.SimpleNamespace(
            MouseButtonPress="press", MouseButtonRelease="release", MouseMove="move"))
        v.Qt = types.SimpleNamespace(MouseButton=types.SimpleNamespace(LeftButton=1, NoButton=0))
        v.QPoint = lambda x, y: (x, y)
        o.save = lambda: None
        o.pump("A")
        o.pump("B")
        self.assertEqual(sent, ["press", "release"])

        # Two lasers (cursors 0 and 1): both presses count, each released separately.
        sent.clear()
        o.last_button_time = {}             # a new scenario, not a duplicate of the click above
        order = iter([(301, 0, "Ctrl"), (301, 1, "Left"), (302, 1, None), (302, 0, None)])
        held = []

        def poll2(handle, ev):
            nxt = next(order, None)
            if nxt is None:
                return (False, ev)
            ev.eventType, ev.data.mouse.cursorIndex, btn = nxt
            if btn:
                held.append(btn)
            return (True, ev)
        o.ov = types.SimpleNamespace(pollNextOverlayEvent=poll2)
        o.button_at = lambda pos: held[-1]
        o.send = lambda w, etype, pos, buttons: sent.append((etype, w))
        o.pump("A")
        self.assertEqual(sent, [("press", "Ctrl"), ("press", "Left"), ("release", "Left"), ("release", "Ctrl")])


class FollowBar(unittest.TestCase):
    def test_switching_steam_and_desktop_tabs_keeps_the_pad_still(self):
        # The main panel shows on the Steam tab and hides on the Desktop tab; the bar stays.
        v = load()
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.apply_pose = lambda: None
        anchors = {v.DASHBOARD_BAR: [[1, 0, 0, 0.0], [0, 1, 0, 1.2], [0, 0, 1, -1.0]],
                   v.DASHBOARD_MAIN: [[1, 0, 0, 0.0], [0, 1, 0, 1.5], [0, 0, 1, -1.4]]}
        main_visible = [True]
        o.dashboard_anchor = lambda keys=v.FOLLOW: next(
            anchors[k] for k in keys if k != v.DASHBOARD_MAIN or main_visible[0])
        o.pose = [[1, 0, 0, 0.1], [0, 1, 0, 0.9], [0, 0, 1, -0.7]]
        o.remember_offset()
        o.follow_dashboard()
        steam_tab = [row[:] for row in o.pose]
        main_visible[0] = False
        o.pose = None
        o.follow_dashboard()
        for a, b in zip(o.pose, steam_tab):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y, places=9)


class MicColour(unittest.TestCase):
    def test_buttons_are_recoloured_before_the_redraw(self):
        v = load()
        o = v.OverlayHost.__new__(v.OverlayHost)
        calls = []
        pad = types.SimpleNamespace(
            layer="nav", mod_state={}, pinned=False, lang="us", scale=1.0, haptic_level=1, collapsed=False,
            cfg={}, click_swap=types.SimpleNamespace(armed=None),
            settings_page=types.SimpleNamespace(isVisible=lambda: False),
            restyle=lambda: calls.append(("restyle", o.dirty)))
        o.pad, o.dirty = pad, False
        for state in ("idle", "recording", "transcribing", "idle"):
            pad.dictation_state = lambda s=state: s
            o.mark_dirty()
            self.assertEqual(calls[-1], ("restyle", False))     # recoloured, then marked for redraw
            self.assertTrue(o.dirty)
            o.dirty = False
        o.mark_dirty()                                             # nothing changed: no redraw
        self.assertFalse(o.dirty)
        self.assertEqual(len(calls), 4)


class Collapse(unittest.TestCase):
    def test_the_chevron_stays_under_the_laser(self):
        """Collapse: the panel shrinks to the chevron (same metres per pixel) and moves so the
        chevron is where it was; Expand puts it back."""
        from PyQt6.QtCore import QPoint, QSize
        v = load()
        o = v.OverlayHost.__new__(v.OverlayHost)
        widths = []
        o.ov = types.SimpleNamespace(setOverlayWidthInMeters=lambda h, m: widths.append(round(m, 4)))
        o.input_handle, o.cover, o.width_m = 1, None, 0.5
        o.pose = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, -1.0]]
        o.apply_pose = o.remember_offset = o.save = lambda: None
        o.log_input = lambda msg: None                           # (not the real pad's log)
        pad = types.SimpleNamespace(expanded_size=QSize(500, 400), toggled=False, pivot=lambda: QPoint(420, 20))
        o.pad = pad
        self.assertFalse(o.fit_size(500, 400))                   # (first picture: nothing to move)
        pad.toggled, pad.pivot = True, (lambda: QPoint(30, 30))
        self.assertTrue(o.fit_size(60, 60))
        self.assertEqual(widths, [0.06])
        self.assertEqual([round(o.pose[i][3], 4) for i in range(3)], [0.17, 0.18, -1.0])
        pad.toggled, pad.pivot = True, (lambda: QPoint(420, 20))
        o.fit_size(500, 400)
        self.assertEqual(widths, [0.06, 0.5])
        self.assertEqual([round(o.pose[i][3], 4) for i in range(3)], [0.0, 0.0, -1.0])


class TakeBackPresses(unittest.TestCase):
    """A grab, the dashboard closing and Close take back the presses lasers hold: each gets a
    release off its key (no click), and the pad lets go of what it holds down (pad.let_go)."""

    def host(self, v):
        o = v.OverlayHost.__new__(v.OverlayHost)
        calls = []
        o.pressed = {0: "↓", 1: "Ctrl"}                          # laser -> the button it holds
        o.send = lambda w, etype, pos, buttons: calls.append((etype, w, pos))
        o.pad = types.SimpleNamespace(let_go=lambda b: calls.append(("let go", b)), pinned=False)
        v.QEvent = types.SimpleNamespace(Type=types.SimpleNamespace(MouseButtonRelease="release"))
        v.Qt = types.SimpleNamespace(MouseButton=types.SimpleNamespace(NoButton=0))
        v.QPoint = lambda x, y: (x, y)
        return o, calls

    def test_grab(self):
        v = load()
        o, calls = self.host(v)
        o.device_matrix = lambda dev: [[1, 0, 0, 0.0], [0, 1, 0, 0.0], [0, 0, 1, 0.0]]
        o.pose, o.depth_axis = [[1, 0, 0, 0.0], [0, 1, 0, 1.0], [0, 0, 1, -1.0]], lambda: None
        o.start_drag(3, grip=True)
        self.assertEqual(calls, [("release", "↓", (-1, -1)), ("let go", "↓"),
                                 ("release", "Ctrl", (-1, -1)), ("let go", "Ctrl")])
        self.assertEqual(o.pressed, {})
        self.assertEqual(o.drag[0], 3)

    def test_dashboard_closing(self):
        v = load()
        o, calls = self.host(v)
        hidden = []
        o.ov = types.SimpleNamespace(isDashboardVisible=lambda: False, hideOverlay=hidden.append)
        o.ticks, o._dash, o.visible, o.cover, o.input_handle = 0, True, True, None, 7
        o.hovered_devices, o.drag, o.grips, o.dirty = {1}, None, None, False
        o.pad.click_swap = types.SimpleNamespace(armed=None)
        o.pad.release_all_mods, o.pad.restyle = (lambda: calls.append("modifiers let go")), (lambda: None)
        o.pump = lambda handle: None
        o.poll()
        self.assertEqual(hidden, [7])
        self.assertEqual([c for c in calls if c[0] == "let go"], [("let go", "↓"), ("let go", "Ctrl")])
        self.assertEqual(calls[-1], "modifiers let go")
        self.assertEqual(o.pressed, {})

    def test_close(self):
        v = load()
        o, calls = self.host(v)
        o.ov = types.SimpleNamespace(destroyOverlay=lambda h: calls.append("destroyed"))
        o.input_handle, o.cover = 7, None
        v.openvr.shutdown = lambda: calls.append("disconnected")
        o.close()
        self.assertEqual(calls, [("release", "↓", (-1, -1)), ("let go", "↓"),
                                 ("release", "Ctrl", (-1, -1)), ("let go", "Ctrl"), "destroyed", "disconnected"])
        self.assertTrue(o.closed)


class AfterClose(unittest.TestCase):
    def test_nothing_reaches_steamvr_after_close(self):
        """Close is pressed inside pump(), and disconnects from SteamVR: the rest of that poll
        mustn't draw, nor may a cover swap or lean easing that comes due with it."""
        v = load()
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.ticks, o._dash, o.visible, o.drag, o.grips, o.dirty, o.input_handle = 1, True, True, None, None, True, 7
        o.pump = lambda handle: setattr(o, "closed", True)       # ✕ pressed
        o.render = lambda: self.fail("drew after Close")
        o.poll()
        touched = []                                             # (SteamVR calls now: a crash)
        o.ov = types.SimpleNamespace(hideOverlay=touched.append, setOverlayFromFile=lambda h, p: touched.append(p))
        o.cover, o.pad = 8, None
        o.uncover("/run/none.png")
        self.assertEqual(touched, [])
        timers = []

        class Timer:
            def __init__(self, parent, interval, timeout):
                self.timeout, self.running = timeout, False
                timers.append(self)

            def start(self):
                self.running = True

            def stop(self):
                self.running = False
        v.QTimer = Timer
        p = math.radians(50)
        o.pose = [[1, 0, 0, 0.0], [0, math.cos(p), math.sin(p), 0.0], [0, -math.sin(p), math.cos(p), 0.0]]
        o.apply_pose = lambda: None
        o.rotate_about_normal(math.radians(3))                   # a slight lean, eased after a grab
        o.ease_level()
        o.apply_pose = lambda: self.fail("moved after Close")
        timers[-1].timeout()
        self.assertFalse(timers[-1].running)


class Reset(unittest.TestCase):
    ANCHOR = [[1, 0, 0, 0.0], [0, 1, 0, 1.2], [0, 0, 1, -1.0]]   # the dashboard bar, facing you

    def host(self, v, anchor, size=(500, 400)):
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.dashboard_anchor = lambda keys=None: anchor
        o.device_matrix = lambda index: [[1, 0, 0, 0.0], [0, 1, 0, 1.6], [0, 0, 1, 0.0]]   # head, looking along -z
        v.openvr.k_unTrackedDeviceIndex_Hmd = 0
        o.width_m, o.input_size = 0.5, size
        o.pad = types.SimpleNamespace(expanded_size=types.SimpleNamespace(width=lambda: 500))
        o.apply_pose = o.remember_offset = o.save = lambda: None
        return o

    def test_a_proper_rotation_with_or_without_the_dashboard(self):
        """The pad's frame: x to your right, facing you; without a dashboard it was mirrored."""
        v = load()
        for anchor in (self.ANCHOR, None):
            o = self.host(v, anchor)
            o.reset_position()
            m = [row[:3] for row in o.pose]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            self.assertAlmostEqual(det, 1.0, places=9, msg=f"anchor {anchor}")
            self.assertEqual([round(m[i][0], 9) for i in range(3)], [1.0, 0.0, 0.0])
            self.assertGreater(m[2][2], 0.0)                     # its face toward you (+z)
            self.assertLess(o.pose[2][3], 0.0)                   # in front of you

    def test_collapsed_it_sits_where_the_pads_top_edge_would(self):
        """Re-centred while collapsed (opened again from the menu), the chevron's top edge goes
        where the pad's would, just below the dashboard, not half a pad's height lower."""
        v = load()
        tops = []
        for w, h in ((500, 400), (60, 60)):
            o = self.host(v, self.ANCHOR, (w, h))
            o.reset_position()
            h_m = h * o.width_m / 500                            # its height as shown (fit_size)
            tops.append([o.pose[i][3] + o.pose[i][1] * h_m / 2 for i in range(3)])
        for a, b in zip(*tops):
            self.assertAlmostEqual(a, b, places=9)


class HoverAfterLanguageChange(unittest.TestCase):
    def test_moving_on_from_a_deleted_button(self):
        """A language change rebuilds the settings page, deleting the button the laser was last
        on: moving on from it raised, which inside the event pump aborts the pad."""
        with mock.patch.dict(os.environ, {"QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}):
            from PyQt6.QtCore import QEvent, Qt
            from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
            app = QApplication.instance() or QApplication([])    # (kept: a dropped one is deleted)
        v = load()
        v.QEvent, v.Qt, v.QApplication = QEvent, Qt, QApplication
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.hover, o.pad = None, types.SimpleNamespace(pulse=lambda *a: None)
        page, key = QWidget(), QPushButton("key")
        done = QPushButton("Done")
        QVBoxLayout(page).addWidget(done)
        o.set_hover(done, 1)
        page.deleteLater()                                       # (retranslate: a new settings page)
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete.value)
        o.set_hover(key, 1)
        self.assertIs(o.hover, key)
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
