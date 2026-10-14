"""Arrow Pad VR overlay geometry: easing a slight sideways lean level after a grab."""
import importlib.util
import math
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


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
        spec = importlib.util.spec_from_file_location("vroverlay", ROOT / "packs/original/arrowpad" / "vroverlay.py")
        v = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v)
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


if __name__ == "__main__":
    unittest.main()


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
