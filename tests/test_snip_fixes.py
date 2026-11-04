"""Screen snip (frame-snip) fixes: the selection's lock goes with its window (a narration window
kept it); a big pasted picture is read at a bounded size, in bounded time, and Paste comes back
whatever goes wrong; the X clipboard owner serves STRING as Latin-1 and answers TEXT as
UTF8_STRING; Copy says "copied" only once the owner holds the clipboard, and falls back to
wl-copy on the desktop; a transparent picture is read on white. Offline: stand-ins for libX11,
Tesseract, Piper and the owner's process."""
import ctypes
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
SNIP = ROOT / "packs/core/snip/frame-snip"
HOME = tempfile.TemporaryDirectory()


def load():
    # (--narrate: the offscreen platform, never the Steam session's display; no i18n: English)
    with mock.patch.object(sys, "argv", ["frame-snip", "--narrate"]), mock.patch.dict(sys.modules, {"i18n": None}), \
            mock.patch.dict(os.environ, {"HOME": HOME.name}):
        mod = load_script(SNIP, "frame_snip_fixes")
    sys.path.remove(os.environ.get("FRAME_TWEAKS_PYLIB") or str(Path(HOME.name) / ".local/share/frame-tweaks/i18n"))
    return mod


fs = load()


_APP = []


def app():
    """The QApplication, kept: one only returned would be collected, and the next widget abort."""
    from PyQt6.QtWidgets import QApplication
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    return _APP[0]


def encoded(img):
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
    buf = QByteArray()
    b = QBuffer(buf)
    b.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(b, "PNG")
    return bytes(buf)


class QuietNarrator:
    """Nothing is spoken (a stand-in for Narrator, made a QObject with its signals per test)."""

    @staticmethod
    def make():
        from PyQt6.QtCore import QObject, pyqtSignal

        class Narrator(QObject):
            progress, finished, failed = pyqtSignal(int, int), pyqtSignal(), pyqtSignal(str, int)

            def __init__(self, text, *a):
                super().__init__()
                self.text, self.stopped = text, False

            def start(self):
                pass

            def cleanup(self):
                pass
        return Narrator


class LockGoesWithTheWindow(unittest.TestCase):
    """Without the VR panel, Narrate opens its window in the selection's process, which held the
    selection's lock for its life: Snip something new and Arrow Pad's Snip then did nothing."""

    def test_a_narration_window_doesnt_keep_the_lock(self):
        from PyQt6.QtCore import QRect
        from PyQt6.QtGui import QImage
        app()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(fs, "RUN", Path(d)), \
                mock.patch.object(fs, "Narrator", QuietNarrator.make()), \
                mock.patch.object(fs, "narration_text", return_value="Words."), \
                mock.patch.object(fs, "PIPER", Path(sys.executable)), mock.patch.object(fs, "VOICE", Path(sys.executable)), \
                mock.patch.object(fs, "vr_panel_available", return_value=False):
            lock = fs.one_selection()
            self.assertIsNotNone(lock)
            image = QImage(200, 100, QImage.Format.Format_RGB32)
            image.fill(0xFFFFFF)
            w = fs.Snip(image, lock)
            w.show()
            self.assertIsNone(fs.one_selection())          # (a selection is open: none stacks on it)
            w.sel = QRect(10, 10, 80, 40)
            w.narrate()
            self.addCleanup(w.popout.close)
            self.assertTrue(w.popout.isVisible())          # (the narration window, in this process)
            again = fs.one_selection()                     # (yet a new selection may start)
            self.assertIsNotNone(again)
            again.close()


class BigPicture(unittest.TestCase):
    """A big pasted picture was read at 2x then 3x (up to 64 MB of PNG): minutes of Tesseract."""

    @staticmethod
    def picture(w, h):
        from PyQt6.QtGui import QImage
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(0xFFFFFF)
        return img

    def sizes(self, img):
        seen = []

        def fake(image, path, psm):
            seen.append(max(image.width(), image.height()))
            return ""                                      # (nothing read: both passes run)
        with mock.patch.object(fs, "TESSERACT", sys.executable), mock.patch.object(fs, "tesseract", fake):
            self.assertEqual(fs.ocr(img), "")
        return seen

    def test_scaled_no_larger_than_the_cap(self):
        seen = self.sizes(self.picture(2500, 1000))
        self.assertEqual(len(seen), 2)
        for side in seen:
            self.assertLessEqual(side, fs.OCR_LONG_SIDE)
            self.assertGreaterEqual(side, 2500)            # (not shrunk)

    def test_already_large_is_read_as_it_is(self):
        self.assertEqual(self.sizes(self.picture(6000, 300)), [6000, 6000])

    def test_small_text_is_still_enlarged(self):
        self.assertEqual(self.sizes(self.picture(300, 100)), [600, 900])

    def test_a_tesseract_that_takes_too_long_reads_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            slow = Path(d) / "tesseract"
            slow.write_text("#!/bin/sh\nexec sleep 20\n")   # (exec: its pipes close when it's ended)
            slow.chmod(0o755)
            start = time.monotonic()
            with mock.patch.object(fs, "TESSERACT", str(slow)), mock.patch.object(fs, "OCR_TIMEOUT", 0.5):
                self.assertEqual(fs.ocr(self.picture(60, 30)), "")
            self.assertLess(time.monotonic() - start, 8)


class PasteComesBack(unittest.TestCase):
    """Anything but RuntimeError in Paste's thread ended it before it answered: Paste stayed greyed out."""

    def test_an_error_while_reading_says_so_and_paste_comes_back(self):
        from PyQt6.QtGui import QImage
        a = app()
        picture = QImage(40, 30, QImage.Format.Format_RGB32)
        picture.fill(0xFFFFFF)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(fs, "Narrator", QuietNarrator.make()), \
                mock.patch.object(fs, "read_clipboard", return_value=("image", encoded(picture))), \
                mock.patch.object(fs, "ocr", side_effect=OSError("Tesseract went away")), \
                mock.patch.object(fs, "NO_TEXT_SNIP", Path(d) / "no-text.png"):
            w = fs.NarrationWindow(QImage(20, 20, QImage.Format.Format_RGB32), "The snip.", 1.0)
            self.addCleanup(w.close)
            w.paste()
            end = time.monotonic() + 10
            while not w.paste_button.isEnabled() and time.monotonic() < end:
                a.processEvents()
                time.sleep(0.01)
            self.assertTrue(w.paste_button.isEnabled())
        self.assertEqual(w.state.text(), "Couldn't read the clipboard.")
        self.assertEqual(w.narrator.text, "The snip.")


class Req(ctypes.Structure):                               # XSelectionRequestEvent
    _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong), ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p), ("owner", ctypes.c_ulong), ("requestor", ctypes.c_ulong),
                ("selection", ctypes.c_ulong), ("target", ctypes.c_ulong), ("property", ctypes.c_ulong),
                ("time", ctypes.c_ulong)]


class OwnerX:
    """libX11 as the clipboard owner sees it: the owner gets the clipboard, then each of asked
    (target names) is requested, then something else is copied. replies: (type name, bytes)."""

    def __init__(self, asked):
        self.atoms, self.names, self.replies = {}, {}, []
        self.queue = [Req(type=30, requestor=5, selection=self.atom("CLIPBOARD"), target=self.atom(t),
                          property=self.atom("P")) for t in asked]
        self.queue.append(Req(type=29))                   # (SelectionClear)

    def atom(self, name):
        if name not in self.atoms:
            self.atoms[name] = 100 + len(self.atoms)
            self.names[self.atoms[name]] = name
        return self.atoms[name]

    def XOpenDisplay(self, name):
        return 1

    def XInternAtom(self, d, name, only):
        return self.atom(name.decode())

    def XDefaultRootWindow(self, d):
        return 1

    def XCreateSimpleWindow(self, *a):
        return 77

    def XSetSelectionOwner(self, *a):
        pass

    def XGetSelectionOwner(self, d, sel):
        return 77

    def XNextEvent(self, d, ev):
        e = self.queue.pop(0)
        ctypes.memmove(ev, ctypes.byref(e), ctypes.sizeof(e))

    def XChangeProperty(self, d, w, prop, typ, fmt, mode, data, n):
        if fmt == 8:
            self.replies.append((self.names[typ.value], ctypes.string_at(data, n)))

    def XSendEvent(self, *a):
        pass

    def XFlush(self, d):
        pass


class OwnerServes(unittest.TestCase):
    """Copy's X clipboard owner served UTF-8 bytes as STRING (Latin-1 by X's rules: "GrÃ¼ÃŸe" in
    a reader that follows them, as Paste's does) and answered TEXT with type TEXT, which tells a
    reader nothing about how to decode it."""

    def own(self, text, asked):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        x = OwnerX(asked)
        r, w = os.pipe()
        self.addCleanup(os.close, r)
        with mock.patch.object(tempfile, "tempdir", tmp.name), mock.patch.object(fs, "x_lib", return_value=x), \
                mock.patch.object(fs, "x_auth_for"), mock.patch.dict(os.environ, {fs.READY_FD: str(w)}):
            d = Path(tempfile.mkdtemp(prefix="snip-clip-"))
            (d / "clip.txt").write_bytes(text.encode())
            self.assertEqual(fs.x_clipboard_owner(str(d), ":0"), 0)
            self.assertNotIn(fs.READY_FD, os.environ)       # (not passed on to anything it starts)
        self.assertEqual(os.read(r, 2), b"1")              # (said it held the clipboard, then closed the pipe)
        return x.replies

    def test_string_is_latin1_text_is_utf8_string(self):
        text = "Grüße, 5 €"
        self.assertEqual(self.own(text, ["STRING", "TEXT", "UTF8_STRING"]),
                         [("STRING", "Grüße, 5 ?".encode("latin-1")),
                          ("UTF8_STRING", text.encode()), ("UTF8_STRING", text.encode())])
        self.assertEqual(fs.clipboard_text("Grüße, 5 ?".encode("latin-1"), "STRING"), "Grüße, 5 ?")


class OwnerReady(unittest.TestCase):
    """Copy said "copied" if the owner's process hadn't ended within half a second, but it imports
    PyQt6 before it even opens the display: on a busy Frame it could fail after that. It's copied
    now once the owner says it holds the clipboard. A stand-in program plays the owner."""

    def owner(self, body):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        f = Path(tmp.name) / "owner.py"
        f.write_text("import os, sys, time\nfd = int(os.environ['FRAME_SNIP_READY_FD'])\n" + body + "\n")
        return f, mock.patch.object(fs.sys, "argv", [str(f)])

    def hand(self, body, **patches):
        patches.setdefault("OWNER_READY_TIMEOUT", fs.OWNER_READY_TIMEOUT)
        f, argv = self.owner(body)
        with argv, mock.patch.multiple(fs, **patches), mock.patch.object(tempfile, "tempdir", str(f.parent)):
            start = time.monotonic()
            got = fs.hand_to_clipboard_owner({"clip.txt": b"x"}, ":0")
        return got, time.monotonic() - start

    def test_slow_to_start_then_failed_is_not_copied(self):
        got, took = self.hand("time.sleep(1.2); sys.exit(1)")
        self.assertIs(got, False)
        self.assertLess(took, 2.9)                         # (its end was seen, not waited out)

    def test_slow_to_start_then_holding_it_is_copied(self):
        self.assertIs(self.hand("time.sleep(1.2); os.write(fd, b'1'); time.sleep(3)")[0], True)

    def test_never_ready_is_not_copied(self):
        got, took = self.hand("time.sleep(30)", OWNER_READY_TIMEOUT=0.5)
        self.assertIs(got, False)
        self.assertLess(took, 5)

    def test_desktop_falls_back_to_wl_copy(self):
        from PyQt6.QtGui import QImage
        img = QImage(10, 10, QImage.Format.Format_RGB32)
        img.fill(0)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "nested_plasma").mkdir()
            (Path(d) / "nested_plasma/xauth_x").write_text("")
            with mock.patch.object(fs, "RUN", Path(d)), mock.patch.object(fs, "nested_wayland", return_value="/w"), \
                    mock.patch.object(fs, "hand_to_clipboard_owner", return_value=False), \
                    mock.patch.object(fs, "to_clipboard", return_value=True) as wl:
                self.assertTrue(fs.copy_image_everywhere(img))
            wl.assert_called_once_with(encoded(img), "image/png")
            with mock.patch.object(fs, "RUN", Path(d)), mock.patch.object(fs, "nested_wayland", return_value="/w"), \
                    mock.patch.object(fs, "hand_to_clipboard_owner", return_value=False), \
                    mock.patch.object(fs, "to_clipboard", return_value=False):
                self.assertFalse(fs.copy_image_everywhere(img))   # (neither: "Couldn't copy")


class TransparentPicture(unittest.TestCase):
    """A pasted picture with transparency (black text on transparent pixels, which are black
    too) read as "the snip is black", and Tesseract saw black on black."""

    def test_read_on_white(self):
        from PyQt6.QtGui import QColor, QImage
        app()
        img = QImage(60, 40, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        for x in range(20, 40):
            for y in range(10, 30):
                img.setPixelColor(x, y, QColor(0, 0, 0))
        seen = []
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(fs, "read_clipboard", return_value=("image", encoded(img))), \
                mock.patch.object(fs, "ocr", side_effect=lambda i: seen.append(i) or ""), \
                mock.patch.object(fs, "NO_TEXT_SNIP", Path(d) / "no-text.png"):
            kind, (shown, text) = fs.pasted_content()
        self.assertEqual(kind, "image")
        self.assertEqual(text, "No text found in the snip.")       # (not "The snip is black")
        self.assertEqual(seen[0].pixelColor(5, 5).lightness(), 255)
        self.assertEqual(seen[0].pixelColor(30, 20).lightness(), 0)
        self.assertEqual(shown.pixelColor(5, 5).lightness(), 255)


if __name__ == "__main__":
    unittest.main()
