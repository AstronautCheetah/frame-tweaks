"""adb-scrcpy/phone-fit: the window size for the phone screen's shape."""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_l = importlib.machinery.SourceFileLoader("pf", str(ROOT / "adb-scrcpy" / "phone-fit"))
pf = importlib.util.module_from_spec(importlib.util.spec_from_loader("pf", _l))
_l.exec_module(pf)


class Fit(unittest.TestCase):
    def test_upright_and_sideways(self):
        self.assertEqual(pf.fit(431, 960), (862, 1920))      # 20:9 phone, upright
        self.assertEqual(pf.fit(960, 431), (1920, 862))      # rotated
        self.assertEqual(pf.fit(1, 1), (1920, 1920))
        self.assertEqual(pf.fit(9, 16, long_side=1080), (608, 1080))


if __name__ == "__main__":
    unittest.main()
