"""Every Konsole Frame Tweaks opens is started with QT_XCB_NO_XI2=1. In VR the controller's laser
reaches X windows as touch, and Konsole took a laser drag to scroll: an install's text couldn't be
selected (or copied). Without XInput 2, Qt gets the pointer the X server makes from the touch, and
a drag selects. (gui/window_logic.py, TERMINAL_ENV.)"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TerminalTouch(unittest.TestCase):
    def test_every_konsole_started_without_xi2(self):
        files = sorted(ROOT.glob("gui/*.py")) + [ROOT / "install.sh"]
        launches = []
        for f in files:
            for n, line in enumerate(f.read_text().splitlines(), 1):
                code = line.split("#", 1)[0] if f.suffix == ".sh" else line
                if re.search(r"""(^|[\s'"(\[])konsole["']?[\s,]+["']?--separate""", code):
                    launches.append((f.name, n, line.strip()))
        self.assertGreaterEqual(len(launches), 5, launches)
        for name, n, line in launches:
            with self.subTest(f"{name}:{n}"):
                self.assertTrue("QT_XCB_NO_XI2=1" in line or "TERMINAL_ENV" in line, line)

    def test_the_setting_itself(self):
        self.assertIn('TERMINAL_ENV = "QT_XCB_NO_XI2=1"', (ROOT / "gui/window_logic.py").read_text())


if __name__ == "__main__":
    unittest.main()
