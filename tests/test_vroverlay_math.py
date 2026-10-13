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
        spec = importlib.util.spec_from_file_location("vroverlay", ROOT / "arrowpad" / "vroverlay.py")
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
                self.data = types.SimpleNamespace(mouse=types.SimpleNamespace(x=10, y=10))
        v.openvr.VREvent_t = Ev
        for k in ("VREvent_MouseMove", "VREvent_MouseButtonDown", "VREvent_MouseButtonUp"):
            setattr(v.openvr, k, getattr(ov, k))
        queues = {"A": [301, 302], "B": [301, 302]}      # one physical click, seen by both

        def poll(handle, ev):
            if queues[handle]:
                ev.eventType = queues[handle].pop(0)
                return (True, ev)
            return (False, ev)
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.ov = types.SimpleNamespace(pollNextOverlayEvent=poll)
        o.last_button_time, o.pressed, o.drag, o.dirty = {}, None, None, False
        o.sizes, o.front = [(100, 100), (100, 100)], 0
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


if __name__ == "__main__":
    unittest.main()
