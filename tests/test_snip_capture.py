"""Screen snip's capture: the focused window from X; a Steam game, which X has no picture of (it
draws straight to gamescope: black, or no picture at all), from gamescope's own screenshot."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import stub  # noqa: E402
from test_bh_media_narrate import fs  # noqa: E402  (frame-snip, loaded offscreen)
from PyQt6.QtGui import QColor, QImage  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402


def picture(colour):
    img = QImage(64, 48, QImage.Format.Format_RGB32)
    img.fill(QColor(colour))
    return img


class Capture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_black_or_not(self):
        self.assertTrue(fs.blank(picture("#000000")))
        self.assertTrue(fs.blank(picture("#050505")))
        self.assertFalse(fs.blank(picture("#202830")))
        dark = picture("#000000")
        dark.setPixelColor(30, 20, QColor("#ffffff"))
        dark.setPixelColor(31, 20, QColor("#ffffff"))
        self.assertFalse(fs.blank(dark.scaled(32, 32)))           # (something drawn on black)

    def test_a_window_x_can_read_stays_from_x(self):
        with mock.patch.object(fs, "capture_focused", lambda: picture("#336699")), \
                mock.patch.object(fs, "capture_gamescope", side_effect=AssertionError("not needed")):
            self.assertEqual(fs.capture().pixelColor(1, 1), QColor("#336699"))

    def test_a_game_comes_from_gamescope(self):
        def fails():
            raise RuntimeError("couldn't read the window's picture")
        for x in (lambda: picture("#000000"), fails):
            with mock.patch.object(fs, "capture_focused", x), \
                    mock.patch.object(fs, "capture_gamescope", lambda: picture("#cc3300")):
                self.assertEqual(fs.capture().pixelColor(1, 1), QColor("#cc3300"))

    def test_gamescopes_screenshot(self):
        png = self.tmp / "shot.png"
        picture("#cc3300").save(str(png))
        stubs = self.tmp / "bin"
        stubs.mkdir()
        stub(stubs, "gamescopectl", f'[ "$1" = screenshot ] && /bin/cp {png} "$2"')
        with mock.patch.dict(os.environ, {"PATH": str(stubs)}), mock.patch.object(fs, "RUN", self.tmp):
            img = fs.capture_gamescope()
            self.assertEqual(img.pixelColor(1, 1), QColor("#cc3300"))
            self.assertEqual(sorted(p.name for p in self.tmp.glob("frame-snip-*.png")), [])      # (not left behind)
        stub(stubs, "gamescopectl", "exit 1")
        with mock.patch.dict(os.environ, {"PATH": str(stubs)}), mock.patch.object(fs, "RUN", self.tmp), \
                mock.patch.object(fs.time, "monotonic", side_effect=[0, 10]):
            with self.assertRaises(RuntimeError):
                fs.capture_gamescope()


if __name__ == "__main__":
    unittest.main()
