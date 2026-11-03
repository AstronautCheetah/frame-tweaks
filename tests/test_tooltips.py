"""lib/tooltips.py: Frame Tweaks' windows show tooltips twice as long as Qt's own (10 s plus 40 ms a
character past 100), recomputed when the text changes; a widget with a duration of its own keeps it."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import helpers  # noqa: E402,F401  (lib/ on sys.path)

try:
    from PyQt6.QtCore import QEvent, QPoint
    from PyQt6.QtGui import QHelpEvent
    from PyQt6.QtWidgets import QApplication, QPushButton
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "needs PyQt6")
class LongerTooltips(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        self.app = QApplication.instance() or QApplication([])
        import tooltips
        self.tooltips = tooltips
        self.filter = tooltips.longer_tooltips(self.app)
        self.addCleanup(self.app.removeEventFilter, self.filter)

    def ask(self, w):
        QApplication.sendEvent(w, QHelpEvent(QEvent.Type.ToolTip, QPoint(1, 1), QPoint(1, 1)))
        return w.toolTipDuration()

    def test_twice_qts_and_follows_the_text(self):
        b = QPushButton("x")
        b.setToolTip("short")
        self.assertEqual(self.ask(b), 20000)
        b.setToolTip("y" * 300)                  # (Qt: 10 s + 40 ms × 200)
        self.assertEqual(self.ask(b), 2 * (10000 + 40 * 200))

    def test_a_duration_of_its_own_stays(self):
        b = QPushButton("x")
        b.setToolTip("mine")
        b.setToolTipDuration(5000)
        self.assertEqual(self.ask(b), 5000)


@unittest.skipIf(QApplication is None, "needs PyQt6")
class Sooner(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        self.app = QApplication.instance() or QApplication([])
        import tooltips
        self.tooltips = tooltips
        self.addCleanup(self.app.removeEventFilter, tooltips.longer_tooltips(self.app))

    def test_they_come_sooner_than_qts_700_ms(self):
        from PyQt6.QtWidgets import QStyle
        self.assertEqual(self.app.style().styleHint(QStyle.StyleHint.SH_ToolTip_WakeUpDelay), self.tooltips.WAKE_MS)
        self.assertLess(self.tooltips.WAKE_MS, 700)


if __name__ == "__main__":
    unittest.main()
