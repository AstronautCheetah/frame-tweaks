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


if __name__ == "__main__":
    unittest.main()
