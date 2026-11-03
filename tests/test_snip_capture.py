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



class TheaterMode(unittest.TestCase):
    """With gamescope's focus on a Steam app (a game, or anything from the "+" menu: Theater mode),
    only that app's windows are shown and get input, so the snip window marks itself as the app's
    (STEAM_GAME = GAMESCOPE_FOCUSED_APP) before it opens; with no focused app, it stays plain."""
    def fake_x(self, appid):
        """libX11 as the snip sees it: GAMESCOPE_FOCUSED_APP on the root holds appid (None: no such
        property); every call is recorded."""
        import ctypes
        x = mock.MagicMock()
        x.XOpenDisplay.return_value = 0x1000
        x.XDefaultRootWindow.return_value = 0x1ab
        x.XInternAtom.side_effect = lambda d, name, only_if_exists: {b"GAMESCOPE_FOCUSED_APP": 301, b"STEAM_GAME": 302}[name]
        self.keep = ctypes.c_ulong(appid or 0)

        def get_property(d, win, atom, offset, length, delete, req_type, rtype, fmt, n, after, prop):
            n._obj.value = 1 if appid else 0
            prop._obj.value = ctypes.addressof(self.keep) if appid else 0
            return 0
        x.XGetWindowProperty.side_effect = get_property
        return x

    def test_the_focused_app_is_read_from_the_root(self):
        with mock.patch.object(fs, "x11", lambda: self.fake_x(57210007)):
            self.assertEqual(fs.focused_app(), 57210007)
        with mock.patch.object(fs, "x11", lambda: self.fake_x(None)):
            self.assertIsNone(fs.focused_app())
        with mock.patch.object(fs, "x11", side_effect=OSError("no libX11")):
            self.assertIsNone(fs.focused_app())

    def test_join_app_sets_steam_game_on_the_window(self):
        import ctypes
        x = self.fake_x(57210007)
        with mock.patch.object(fs, "x11", lambda: x):
            fs.join_app(0x6e00007, 57210007)
        call = x.XChangeProperty.call_args[0]
        self.assertEqual((call[1].value, call[2].value, call[3].value, call[4], call[5], call[7]),
                         (0x6e00007, 302, 6, 32, 0, 1))                  # (window, STEAM_GAME, CARDINAL, 32-bit, replace, one value)
        self.assertEqual(ctypes.cast(call[6], ctypes.POINTER(ctypes.c_ulong))[0], 57210007)
        x.XFlush.assert_called_once()
        x.XCloseDisplay.assert_called_once()

    def test_the_window_is_tagged_only_with_an_app_in_focus(self):
        window = mock.Mock()
        window.winId.return_value = 0x6e00007
        joined = []
        with mock.patch.object(fs, "focused_app", lambda: 57210007), \
                mock.patch.object(fs, "join_app", lambda win, appid: joined.append((win, appid))):
            self.assertEqual(fs.tag_for_theater(window), 57210007)
        self.assertEqual(joined, [(0x6e00007, 57210007)])
        joined.clear()
        with mock.patch.object(fs, "focused_app", lambda: None), \
                mock.patch.object(fs, "join_app", lambda win, appid: joined.append((win, appid))):
            self.assertIsNone(fs.tag_for_theater(window))               # (the desktop or a plain window has the focus)
        with mock.patch.object(fs, "focused_app", lambda: 57210007), \
                mock.patch.object(fs, "join_app", lambda win, appid: joined.append((win, appid))), \
                mock.patch.dict(os.environ, {"SFT_SNIP_NO_APP_TAG": "1"}):
            self.assertIsNone(fs.tag_for_theater(window))               # (turned off)
        self.assertEqual(joined, [])
        with mock.patch.object(fs, "focused_app", lambda: 57210007), \
                mock.patch.object(fs, "join_app", mock.Mock(side_effect=OSError("no display"))):
            self.assertIsNone(fs.tag_for_theater(window))               # (X unreachable: a plain window, as before)

if __name__ == "__main__":
    unittest.main()
