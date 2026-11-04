"""Narrate's Paste (frame-snip): the clipboard's text or picture, from desktop mode's clipboard
while desktop mode runs, else from the VR session's own X clipboard, read by a process of its own
so an owner that never answers can't stall the panel. A picture is read like a snip (OCR, and
"no text found"). Offline: wl-paste, the X reader's process and Tesseract are stand-ins; the X
reader itself runs against a stand-in libX11, and, where Xvfb is installed, against a real X
server with frame-snip's own clipboard owner on the other end."""
import ctypes
import os
import shutil
import subprocess
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
        mod = load_script(SNIP, "frame_snip_paste")
    sys.path.remove(os.environ.get("FRAME_TWEAKS_PYLIB") or str(Path(HOME.name) / ".local/share/frame-tweaks/i18n"))
    return mod


fs = load()


def png(w=40, h=30):
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
    from PyQt6.QtGui import QImage
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(0xFFFFFF)
    buf = QByteArray()
    b = QBuffer(buf)
    b.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(b, "PNG")
    return bytes(buf)


class Choice(unittest.TestCase):
    def test_the_type_asked_for(self):
        cases = [
            (["text/plain", "image/png", "text/html"], ("image", "image/png")),
            # (a browser's Copy Image: the picture, not its address offered as text)
            (["text/html", "text/plain;charset=utf-8", "image/jpeg", "image/bmp"], ("image", "image/jpeg")),
            (["image/bmp", "image/png"], ("image", "image/png")),
            (["TARGETS", "TIMESTAMP", "image/x-portable-pixmap"], ("image", "image/x-portable-pixmap")),
            (["STRING", "UTF8_STRING", "TEXT"], ("text", "UTF8_STRING")),
            (["text/plain;charset=UTF-8", "text/plain"], ("text", "text/plain;charset=UTF-8")),
            (["STRING"], ("text", "STRING")),
            ([" text/plain \n", ""], ("text", "text/plain")),
            (["text/uri-list", "x-special/gnome-copied-files", "TARGETS"], None),
            ([], None),
        ]
        for types, want in cases:
            with self.subTest(types):
                self.assertEqual(fs.clipboard_choice(types), want)

    def test_string_is_latin1_the_rest_utf8(self):
        self.assertEqual(fs.clipboard_text("café".encode("latin-1"), "STRING"), "café")
        self.assertEqual(fs.clipboard_text("café\0\n".encode(), "UTF8_STRING"), "café")


class WhichClipboard(unittest.TestCase):
    def test_without_desktop_mode_the_vr_sessions_x_clipboard(self):
        for env, want in ((":0", ":0"), (":1", ":1"), (":2", ":0")):
            with self.subTest(env), mock.patch.object(fs, "nested_wayland", return_value=None), \
                    mock.patch.dict(os.environ, {"DISPLAY": env}), \
                    mock.patch.object(fs, "desktop_paste") as desk, \
                    mock.patch.object(fs, "x_clipboard_paste", return_value=("text", "hi")) as xp:
                self.assertEqual(fs.read_clipboard(), ("text", "hi"))
            desk.assert_not_called()
            xp.assert_called_once_with(want)

    def test_desktop_modes_clipboard_first_then_the_vr_sessions(self):
        with mock.patch.object(fs, "nested_wayland", return_value="/run/x/wayland-0"), \
                mock.patch.object(fs, "desktop_paste", return_value=("image", b"p")), \
                mock.patch.object(fs, "x_clipboard_paste") as xp:
            self.assertEqual(fs.read_clipboard(), ("image", b"p"))
        xp.assert_not_called()
        with mock.patch.object(fs, "nested_wayland", return_value="/run/x/wayland-0"), \
                mock.patch.object(fs, "desktop_paste", return_value=("empty", None)), \
                mock.patch.object(fs, "x_clipboard_paste", return_value=("text", "from VR")):
            self.assertEqual(fs.read_clipboard(), ("text", "from VR"))

    def test_with_nothing_to_read_the_most_telling_reason(self):
        for desk, vr, want in ((("empty", None), ("failed", None), "failed"),
                               (("other", None), ("empty", None), "other"),
                               (("failed", None), ("big", None), "big"),
                               (("empty", None), ("empty", None), "empty")):
            with self.subTest((desk, vr)), mock.patch.object(fs, "nested_wayland", return_value="/run/x/wayland-0"), \
                    mock.patch.object(fs, "desktop_paste", return_value=desk), \
                    mock.patch.object(fs, "x_clipboard_paste", return_value=vr):
                self.assertEqual(fs.read_clipboard(), (want, None))


class DesktopPaste(unittest.TestCase):
    def run_with(self, listed, data=b"", listed_code=0):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            if "--list-types" in cmd:
                return subprocess.CompletedProcess(cmd, listed_code, listed.encode(), b"")
            return subprocess.CompletedProcess(cmd, 0, data, b"")
        with mock.patch.object(fs, "nested_wayland", return_value="/run/x/wayland-0"), \
                mock.patch.object(fs, "wl_tool", return_value="/bin/wl-paste"), \
                mock.patch.object(fs.subprocess, "run", side_effect=run):
            return fs.desktop_paste(), calls

    def test_the_best_type_is_asked_for(self):
        got, calls = self.run_with("text/plain\nimage/png\nimage/bmp\n", b"\x89PNG...")
        self.assertEqual(got, ("image", b"\x89PNG..."))
        self.assertEqual(calls[-1][-2:], ["--type", "image/png"])
        got, calls = self.run_with("UTF8_STRING\ntext/plain;charset=utf-8\n", "héllo\n".encode())
        self.assertEqual(got, ("text", "héllo"))
        self.assertEqual(calls[-1][-1], "text/plain;charset=utf-8")

    def test_empty_neither_or_too_big(self):
        self.assertEqual(self.run_with("", listed_code=1)[0], ("empty", None))      # ("Nothing is copied")
        self.assertEqual(self.run_with("text/uri-list\n")[0], ("other", None))
        self.assertEqual(self.run_with("text/plain\n", b"  \n")[0], ("empty", None))
        with mock.patch.object(fs, "PASTE_LIMIT", 4):
            self.assertEqual(self.run_with("image/png\n", b"12345")[0], ("big", None))


class XPasteProcess(unittest.TestCase):
    """x_clipboard_paste: the reader's process, its answer read back, and given up on in time."""

    def answer(self, out, code=0, raises=None):
        with mock.patch.object(fs.subprocess, "run", side_effect=raises,
                               return_value=subprocess.CompletedProcess([], code, out, b"")) as run:
            got = fs.x_clipboard_paste(":0")
        return got, run

    def test_its_answer(self):
        image = png()
        self.assertEqual(self.answer(b"image\n" + image)[0], ("image", image))
        self.assertEqual(self.answer("text\nhé\nthere".encode())[0], ("text", "hé\nthere"))
        for kind in ("empty", "other", "big", "failed"):
            self.assertEqual(self.answer(kind.encode() + b"\n")[0], (kind, None))
        got, run = self.answer(b"empty\n")
        self.assertEqual(run.call_args.args[0][-2:], ["--x-paste", ":0"])
        self.assertEqual(run.call_args.kwargs["timeout"], fs.PASTE_TIMEOUT + 1)

    def test_anything_else_is_failed(self):
        for out, code in ((b"", 0), (b"image", 0), (b"nonsense\n", 0), (b"text\nhi", 1)):
            with self.subTest(out):
                self.assertEqual(self.answer(out, code)[0], ("failed", None))

    def test_a_reader_that_doesnt_end_is_given_up_on(self):
        self.assertEqual(self.answer(b"", raises=subprocess.TimeoutExpired("frame-snip", 6))[0], ("failed", None))

    def test_it_takes_only_an_x_display(self):
        with mock.patch("builtins.print"), mock.patch.object(fs, "read_x_clipboard") as read:
            self.assertEqual(fs.x_paste("remote:0"), 1)
        read.assert_not_called()


class FakeX:
    """libX11 with one clipboard owner: offers (target name: bytes; TARGETS lists them unless
    targets=False, and it refuses TARGETS), in INCR parts of `parts` bytes if given; silent: it
    never answers."""
    XA_ATOM = 4

    def __init__(self, offers=None, owner=True, targets=True, parts=None, silent=False):
        self.offers, self.owner, self.targets, self.parts, self.silent = offers or {}, owner, targets, parts, silent
        self.atoms, self.names, self.queue, self.keep, self.prop, self.chunks = {}, {}, [], [], None, None
        self.r, self.w = os.pipe()                 # (never written: select only waits)
        self.closed = False

    def close(self):
        os.close(self.r)
        os.close(self.w)

    @staticmethod
    def v(a):
        return getattr(a, "value", a)

    def XOpenDisplay(self, name):
        return 1

    def XInternAtom(self, d, name, only):
        name = name.decode()
        if name not in self.atoms:
            self.atoms[name] = 100 + len(self.atoms)
            self.names[self.atoms[name]] = name
        return self.atoms[name]

    def XGetSelectionOwner(self, d, sel):
        return 9 if self.owner else 0

    def XDefaultRootWindow(self, d):
        return 1

    def XCreateSimpleWindow(self, *a):
        return 77

    def XSelectInput(self, *a):
        pass

    def XFlush(self, d):
        pass

    def XFree(self, p):
        pass

    def XCloseDisplay(self, d):
        self.closed = True

    def XConnectionNumber(self, d):
        return self.r

    def XPending(self, d):
        return len(self.queue)

    def XNextEvent(self, d, ev):
        e = self.queue.pop(0)
        ctypes.memmove(ev, ctypes.byref(e), ctypes.sizeof(e))

    def XGetAtomName(self, d, a):
        b = ctypes.create_string_buffer(self.names[self.v(a)].encode())
        self.keep.append(b)
        return ctypes.addressof(b)

    def notify(self, target, prop):
        self.queue.append(fs.XSelectionEvent(type=31, requestor=77, selection=self.atoms["CLIPBOARD"],
                                             target=target, property=prop))

    def property_event(self, state):
        self.queue.append(fs.XPropertyEvent(type=28, window=77, atom=self.atoms["FRAME_SNIP_PASTE"], state=state))

    def XConvertSelection(self, d, sel, target, prop, win, t):
        target, prop = self.v(target), self.v(prop)
        name = self.names[target]
        if self.silent:
            return
        if name == "TARGETS" and self.targets:
            atoms = [self.XInternAtom(d, b"TARGETS", 0)] + [self.XInternAtom(d, n.encode(), 0) for n in self.offers]
            self.prop = (self.XA_ATOM, 32, bytes((ctypes.c_ulong * len(atoms))(*atoms)), len(atoms))
        elif name in self.offers:
            data = self.offers[name]
            if self.parts:
                self.chunks = [data[i:i + self.parts] for i in range(0, len(data), self.parts)] + [b""]
                self.prop = (self.XInternAtom(d, b"INCR", 0), 32, bytes(ctypes.c_ulong(len(data))), 1)
                self.incr_target = target
            else:
                self.prop = (target, 8, data, len(data))
        else:
            return self.notify(target, 0)
        self.notify(target, prop)

    def XGetWindowProperty(self, d, w, prop, offset, length, delete, req, typ, fmt, n, after, ptr):
        t, f, data, count = self.prop or (0, 0, b"", 0)
        shown = data[:self.v(length) * 4] if f == 8 else data
        buf = ctypes.create_string_buffer(shown, max(1, len(shown)))
        self.keep.append(buf)
        typ._obj.value, fmt._obj.value = t, f
        n._obj.value = len(shown) if f == 8 else count
        after._obj.value = len(data) - len(shown)
        ptr._obj.value = ctypes.addressof(buf) if self.prop else None
        if self.v(delete) and not after._obj.value and self.prop:
            self.prop = None
            self.property_event(1)                 # (its own delete: not a new part)
            if self.chunks:                        # an INCR owner answers a delete with the next part
                part = self.chunks.pop(0)
                self.prop = (self.incr_target, 8, part, len(part))
                self.property_event(0)


class XReader(unittest.TestCase):
    def read(self, x, **kw):
        self.addCleanup(x.close)
        got = fs.read_x_clipboard(":0", x=x, **kw)
        self.assertTrue(x.closed)
        return got

    def test_a_picture_before_text(self):
        image = png()
        self.assertEqual(self.read(FakeX({"UTF8_STRING": b"addr", "image/bmp": b"BM..", "image/png": image})),
                         ("image", image))

    def test_text(self):
        self.assertEqual(self.read(FakeX({"STRING": b"x", "UTF8_STRING": "héllo ".encode()})), ("text", "héllo"))

    def test_empty_neither_or_refused(self):
        self.assertEqual(self.read(FakeX(owner=False)), ("empty", None))
        self.assertEqual(self.read(FakeX({"text/uri-list": b"file:///x"})), ("other", None))
        self.assertEqual(self.read(FakeX({"UTF8_STRING": b"   "})), ("empty", None))

    def test_an_owner_that_doesnt_list_its_types_gives_plain_text(self):
        self.assertEqual(self.read(FakeX({"UTF8_STRING": b"old"}, targets=False)), ("text", "old"))
        self.assertEqual(self.read(FakeX({"STRING": "café".encode("latin-1")}, targets=False)), ("text", "café"))
        self.assertEqual(self.read(FakeX({"image/png": b"x"}, targets=False)), ("other", None))

    def test_a_big_picture_in_parts(self):
        image = png(300, 200)
        self.assertEqual(self.read(FakeX({"image/png": image}, parts=97)), ("image", image))

    def test_too_big(self):
        with mock.patch.object(fs, "PASTE_LIMIT", 1000):
            self.assertEqual(self.read(FakeX({"image/png": b"x" * 1500}, parts=100)), ("big", None))
            self.assertEqual(self.read(FakeX({"image/png": b"x" * 1500})), ("big", None))

    def test_an_owner_that_never_answers_is_given_up_on(self):
        start = time.monotonic()
        self.assertEqual(self.read(FakeX({"UTF8_STRING": b"x"}, silent=True), timeout=0.3), ("failed", None))
        self.assertLess(time.monotonic() - start, 3)


class PanelPaste(unittest.TestCase):
    """The panel's Paste: in a thread, then text read as it is and a picture read like a snip."""

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from PyQt6.QtCore import QObject, pyqtSignal

        class Narrator(QObject):                   # (nothing is spoken)
            progress, finished, failed = pyqtSignal(int, int), pyqtSignal(), pyqtSignal(str, int)

            def __init__(self, text, *a):
                super().__init__()
                self.text, self.stopped = text, False

            def start(self):
                pass

            def cleanup(self):
                pass
        p = mock.patch.object(fs, "Narrator", Narrator)
        p.start()
        self.addCleanup(p.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        from PyQt6.QtGui import QImage
        self.w = fs.NarrationWindow(QImage(20, 20, QImage.Format.Format_RGB32), "The snip.", 1.0)

    def paste(self, clipboard, ocr=None):
        with mock.patch.object(fs, "read_clipboard", return_value=clipboard), \
                mock.patch.object(fs, "ocr", return_value=ocr), \
                mock.patch.object(fs, "NO_TEXT_SNIP", self.tmp / "no-text.png"), \
                mock.patch.object(fs, "tesseract_missing") as missing:
            self.w.paste()
            self.assertFalse(self.w.paste_button.isEnabled())       # (one paste at a time)
            end = time.monotonic() + 10
            while not self.w.paste_button.isEnabled() and time.monotonic() < end:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertTrue(self.w.paste_button.isEnabled(), self.w.state.text())
        return missing

    def test_text_is_read_as_it_is(self):
        self.paste(("text", "Pasted words."))
        self.assertIsNone(self.w.image)
        self.assertEqual(self.w.narrator.text, "Pasted words.")

    def test_a_picture_is_read_like_a_snip(self):
        self.paste(("image", png(50, 40)), ocr="Words in the picture.")
        self.assertEqual((self.w.image.width(), self.w.image.height()), (50, 40))
        self.assertEqual(self.w.view, "image")
        self.assertEqual(self.w.narrator.text, "Words in the picture.")

    def test_a_picture_without_text_says_why_and_is_kept(self):
        self.paste(("image", png()), ocr="")
        self.assertEqual(self.w.narrator.text, "No text found in the snip.")
        self.assertTrue((self.tmp / "no-text.png").exists())

    def test_without_tesseract_it_offers_to_reinstall(self):
        missing = self.paste(("image", png()), ocr=None)
        missing.assert_called_once()
        self.assertEqual(self.w.narrator.text, "The snip.")        # (what was read stays)

    def test_nothing_to_read_says_why(self):
        for got, said in ((("empty", None), "The clipboard is empty."),
                          (("other", None), "The clipboard has neither text nor a picture."),
                          (("failed", None), "Couldn't read the clipboard."),
                          (("big", None), "What's on the clipboard is too big to paste."),
                          (("image", b"not a picture"), "Couldn't read the picture on the clipboard.")):
            with self.subTest(got):
                self.paste(got)
                self.assertEqual(self.w.state.text(), said)
                self.assertEqual(self.w.narrator.text, "The snip.")


@unittest.skipUnless(shutil.which("Xvfb") and sys.platform.startswith("linux"), "needs Xvfb")
class RealX(unittest.TestCase):
    """frame-snip's own X clipboard owner (Copy without desktop mode) on one end, Paste's reader
    on the other, on a private Xvfb display."""

    def setUp(self):
        r, w = os.pipe()
        xvfb = subprocess.Popen(["Xvfb", "-displayfd", str(w), "-screen", "0", "64x64x24", "-nolisten", "tcp"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, pass_fds=(w,))
        os.close(w)
        self.addCleanup(lambda: (xvfb.terminate(), xvfb.wait(10)))
        with os.fdopen(r) as f:
            number = f.readline().strip()
        if not number.isdigit():
            self.skipTest("Xvfb didn't start")
        self.display = ":" + number
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        import PyQt6
        self.env = dict(os.environ, TMPDIR=str(self.tmp), FRAME_TWEAKS_PYLIB=str(ROOT / "lib"),
                        HOME=str(self.tmp), PYTHONPATH=str(Path(PyQt6.__file__).resolve().parent.parent))
        self.env.pop("XAUTHORITY", None)

    def own(self, blobs):
        d = Path(tempfile.mkdtemp(prefix="snip-clip-", dir=self.tmp))
        for name, data in blobs.items():
            (d / name).write_bytes(data)
        owner = subprocess.Popen([sys.executable, str(SNIP), "--x-clipboard", str(d), self.display], env=self.env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: (owner.kill(), owner.wait(10)))

    def paste(self):
        """What Paste reads, through its own process (frame-snip --x-paste), once the owner holds it."""
        end = time.monotonic() + 15
        with mock.patch.object(fs.sys, "argv", [str(SNIP)]), mock.patch.dict(os.environ, self.env, clear=True):
            while True:
                got = fs.x_clipboard_paste(self.display)
                if got[0] != "empty" or time.monotonic() > end:
                    return got
                time.sleep(0.1)

    def test_a_picture_copied_is_pasted(self):
        image = png(120, 80)
        self.own({"clip.png": image, "clip.bmp": b"BM", "clip.html": b"<img>", "clip.txt": b"not this"})
        self.assertEqual(self.paste(), ("image", image))

    def test_text_copied_is_pasted(self):
        self.own({"clip.txt": "Grüße aus VR".encode()})
        self.assertEqual(self.paste(), ("text", "Grüße aus VR"))

    def test_nothing_copied(self):
        self.assertEqual(fs.read_x_clipboard(self.display), ("empty", None))


if __name__ == "__main__":
    unittest.main()
