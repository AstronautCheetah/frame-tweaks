"""Screen snip (frame-snip) hands a snip to its narration panel (and an image to its X clipboard
owner) in a folder it makes in the temporary folder, and that's all the panel takes: a path
anywhere else, over the panel's socket (any program of yours can write to it) or on the command
line, is refused, never read aloud, and its folder never deleted; nor is a file in its folder
that's a link, or a FIFO (switched in after the checks, too). Offline, in throwaway folders: the
panel is a separate process with stand-ins for SteamVR and Piper, and its socket is in its own
temporary folder (never the real panel's)."""
import json
import os
import socket
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
from helpers import load_script, stub  # noqa: E402
SNIP = ROOT / "packs/core/snip/frame-snip"
HOME = tempfile.TemporaryDirectory()
SECRET = "This is the text of a file of yours."
FAKE_OPENVR = '''from unittest import mock
k_unTrackedDeviceIndex_Hmd, k_unTrackedDeviceIndexInvalid = 0, 0xFFFFFFFF
_vr = mock.MagicMock()
_vr.VROverlay.return_value.findOverlay.side_effect = RuntimeError("no dashboard")
_vr.VROverlay.return_value.pollNextOverlayEvent.return_value = (False, None)
_vr.VRSystem.return_value.getDeviceToAbsoluteTrackingPose.return_value = []
_vr.VRSystem.return_value.getTrackedDeviceIndexForControllerRole.return_value = k_unTrackedDeviceIndexInvalid


def __getattr__(name):
    return getattr(_vr, name)
'''


def load():
    # (--narrate: the offscreen platform, never the Steam session's display; no i18n: English)
    with mock.patch.object(sys, "argv", ["frame-snip", "--narrate"]), mock.patch.dict(sys.modules, {"i18n": None}), \
            mock.patch.dict(os.environ, {"HOME": HOME.name}):
        mod = load_script(SNIP, "frame_snip_handover")
    sys.path.remove(os.environ.get("FRAME_TWEAKS_PYLIB") or str(Path(HOME.name) / ".local/share/frame-tweaks/i18n"))
    return mod


fs = load()


def snip_folder(parent, name, text="A snip's text."):
    """A folder as Narrate makes one: snip.png and text.txt."""
    from PyQt6.QtGui import QImage
    d = Path(parent) / name
    d.mkdir(mode=0o700)
    QImage(20, 20, QImage.Format.Format_RGB32).save(str(d / "snip.png"))
    (d / "text.txt").write_text(text)
    return d


class Handover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.t = Path(tmp.name)
        self.tmpdir = self.t / "tmp"                     # (the temporary folder, as frame-snip sees it)
        self.tmpdir.mkdir()
        p = mock.patch.object(tempfile, "tempdir", str(self.tmpdir))
        p.start()
        self.addCleanup(p.stop)
        self.yours = snip_folder(self.t, "Documents", SECRET)      # (a folder of yours, with a picture in it)

    def test_a_snip_narrate_made_is_taken_and_its_folder_removed(self):
        d = Path(tempfile.mkdtemp(prefix="snip-narrate-in-"))          # (as Narrate makes it)
        d.rmdir()
        snip_folder(d.parent, d.name, "Read this.")
        image, text = fs.handed_snip(str(d / "snip.png"), str(d / "text.txt"))
        self.assertEqual(text, "Read this.")
        self.assertFalse(image.isNull())
        self.assertFalse(d.exists())

    def test_anything_else_is_refused_and_left_alone(self):
        outside = (self.yours / "snip.png", self.yours / "text.txt")
        named = snip_folder(self.tmpdir, "snip-narrate-in-mine")
        elsewhere = snip_folder(self.t, "snip-narrate-in-elsewhere")          # (not in the temporary folder)
        (self.tmpdir / "sub").mkdir()
        nested = snip_folder(self.tmpdir / "sub", "snip-narrate-in-x")        # (nor right in it)
        link = self.tmpdir / "snip-narrate-in-link"
        link.symlink_to(self.yours)                                           # (a folder of yours by another name)
        cases = [outside,
                 (named / "snip.png", self.yours / "text.txt"),               # (its text from elsewhere)
                 (named / ".." / ".." / "Documents" / "snip.png", named / "text.txt"),
                 (elsewhere / "snip.png", elsewhere / "text.txt"),
                 (nested / "snip.png", nested / "text.txt"),
                 (link / "snip.png", link / "text.txt"),
                 (self.tmpdir / "snip.png", self.tmpdir / "text.txt"),
                 (self.tmpdir / "snip-clip-x" / "snip.png", self.tmpdir / "snip-clip-x" / "text.txt")]
        for image, text in cases:
            with self.subTest(image=str(image), text=str(text)):
                with self.assertRaises(ValueError):
                    fs.handed_snip(str(image), str(text))
        for d in (self.yours, named, elsewhere, nested):
            self.assertTrue((d / "snip.png").exists() and (d / "text.txt").exists(), d)
        self.assertTrue(link.is_symlink())

    def test_a_file_in_its_folder_that_leads_elsewhere_is_refused(self):
        d = Path(tempfile.mkdtemp(prefix="snip-narrate-in-"))
        (d / "snip.png").symlink_to(self.yours / "snip.png")
        (d / "text.txt").symlink_to(self.yours / "text.txt")
        with self.assertRaises(ValueError):
            fs.handed_snip(str(d / "snip.png"), str(d / "text.txt"))
        self.assertTrue(d.exists())
        self.assertEqual((self.yours / "text.txt").read_text(), SECRET)

    def test_switched_for_a_link_after_the_checks_its_not_read_through(self):
        """Checked by name, then opened by name: text.txt, or the whole folder, switched for a link
        in between (anything that can write in the temporary folder could) was read through."""
        real = fs.read_handed
        for what in ("text.txt", "folder"):
            with self.subTest(what=what):
                d = Path(tempfile.mkdtemp(prefix="snip-narrate-in-"))
                d.rmdir()
                snip_folder(d.parent, d.name)

                def switch_then_read(folder, files):
                    if what == "folder":
                        folder.rename(folder.with_name("old"))
                        folder.symlink_to(self.yours)
                    else:
                        (folder / "text.txt").unlink()
                        (folder / "text.txt").symlink_to(self.yours / "text.txt")
                    return real(folder, files)
                with mock.patch.object(fs, "read_handed", switch_then_read), self.assertRaises(ValueError):
                    fs.handed_snip(str(d / "snip.png"), str(d / "text.txt"))
                self.assertTrue((self.yours / "snip.png").exists())
                self.assertEqual((self.yours / "text.txt").read_text(), SECRET)
                if what == "folder":
                    d.unlink()
                    d.with_name("old").rename(d)

    def test_a_fifo_in_its_folder_doesnt_keep_it_waiting(self):
        d = Path(tempfile.mkdtemp(prefix="snip-narrate-in-"))
        d.rmdir()
        snip_folder(d.parent, d.name)
        (d / "text.txt").unlink()
        os.mkfifo(d / "text.txt")
        with self.assertRaises(ValueError):
            fs.handed_snip(str(d / "snip.png"), str(d / "text.txt"))

    def test_the_x_clipboard_owner_takes_only_its_own_folder(self):
        """frame-snip --x-clipboard DIR read DIR's pictures, then deleted DIR, whatever it was."""
        err = []
        with mock.patch("builtins.print", side_effect=lambda *a, **k: err.append(" ".join(map(str, a)))):
            self.assertEqual(fs.x_clipboard_owner(str(self.yours)), 1)
        self.assertTrue((self.yours / "snip.png").exists())
        self.assertIn("not a folder frame-snip made", err[0])
        d = Path(tempfile.mkdtemp(prefix="snip-clip-"))
        self.assertEqual(fs.made_here(d, "snip-clip-"), d.resolve())


class VrClipboard(unittest.TestCase):
    """Without desktop mode, Copy text and Copy image went nowhere ("Couldn't copy (is desktop mode
    running?)"): now they go on the VR session's own X clipboard, for its floating windows."""

    def test_text_without_desktop_mode_goes_to_the_vr_session(self):
        handed = []
        with mock.patch.object(fs, "nested_wayland", return_value=None), \
             mock.patch.object(fs, "hand_to_clipboard_owner", side_effect=lambda b, d: handed.append((b, d)) or True), \
             mock.patch.dict(os.environ, {"DISPLAY": ":0"}):
            self.assertTrue(fs.copy_text_everywhere("héllo"))
        self.assertEqual(handed, [({"clip.txt": "héllo".encode()}, ":0")])

    def test_text_with_desktop_mode_still_goes_to_the_desktop(self):
        with mock.patch.object(fs, "nested_wayland", return_value="/run/x/wayland-0"), \
             mock.patch.object(fs, "to_clipboard", return_value=True) as wl, \
             mock.patch.object(fs, "hand_to_clipboard_owner") as owner:
            self.assertTrue(fs.copy_text_everywhere("hi"))
        wl.assert_called_once_with(b"hi", "text/plain;charset=utf-8")
        owner.assert_not_called()

    def test_the_vr_display(self):
        for env, want in ((":0", ":0"), (":1", ":1"), (":2", ":0"), ("", ":0"), ("host:0", ":0")):
            with self.subTest(env), mock.patch.dict(os.environ, {"DISPLAY": env}):
                self.assertEqual(fs.vr_display(), want)

    # (copied only once the owner holds the clipboard: test_snip_fixes.py, OwnerReady)

    def test_the_owner_takes_only_an_x_display(self):
        d = Path(tempfile.mkdtemp(prefix="snip-clip-"))
        self.addCleanup(lambda: d.exists() and d.rmdir())
        with mock.patch("builtins.print"):
            self.assertEqual(fs.x_clipboard_owner(str(d), "remote:0"), 1)
        self.assertTrue(d.exists())                    # (refused before reading or removing it)


class OpenPanel(unittest.TestCase):
    def test_the_panels_socket_takes_only_a_snip_narrate_made(self):
        """A panel is open; a request names a file of yours and a picture in a folder of yours: it
        isn't read aloud and the folder stays. The next snip from Narrate is still read."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        t = Path(tmp.name)
        sock = t / f"frame-snip-narration-{os.getuid()}"      # (TMPDIR=t: not the real panel's)
        if len(str(sock)) > 100:
            self.skipTest("temporary folder's path too long for a local socket")
        home, stubs, vr = t / "home", t / "stubs", t / "vr"
        speech = home / ".local/share/frame-tweaks/speech"
        for d in (speech / "piper", stubs, vr, home / ".config/frame-tweaks"):
            d.mkdir(parents=True)
        log = t / "said"
        # Piper: writes the sound file it's asked for, and notes the text it was given
        stub(speech / "piper", "piper", 'while [ $# -gt 0 ]; do [ "$1" = --output_file ] && out=$2; shift; done\n'
                                        f'/bin/cat > "$out"; /bin/cat "$out" >> {log}; echo >> {log}')
        (speech / "voice.onnx").write_text("")
        stub(stubs, "pw-play", "exec /bin/sleep 0.2")
        (vr / "openvr.py").write_text(FAKE_OPENVR)
        first = snip_folder(t, "snip-narrate-in-1", "The first snip is read.")
        yours = snip_folder(t / "home", "Documents", SECRET)
        boot = (f"import runpy, sys\nsys.path.insert(0, {str(vr)!r})\nimport openvr\n"
                f"assert openvr.__file__.startswith({str(vr)!r}), openvr.__file__   # (never the real one)\n"
                f"sys.argv = ['frame-snip', '--narrate', {str(first / 'snip.png')!r}, {str(first / 'text.txt')!r}]\n"
                f"runpy.run_path({str(SNIP)!r}, run_name='__main__')\n")
        import PyQt6
        env = {"HOME": str(home), "PATH": str(stubs), "TMPDIR": str(t), "QT_QPA_PLATFORM": "offscreen",
               "FRAME_TWEAKS_PYLIB": str(ROOT / "lib"), "FRAME_TWEAKS_LANGUAGE": "en",
               "PYTHONPATH": str(Path(PyQt6.__file__).resolve().parent.parent)}
        out = open(t / "panel.out", "w")
        self.addCleanup(out.close)
        panel = subprocess.Popen([sys.executable, "-c", boot], env=env, stdout=out, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: (panel.kill(), panel.wait(10)))

        def wait_for(cond, seconds=20):
            end = time.monotonic() + seconds
            while time.monotonic() < end and panel.poll() is None:
                if cond():
                    return True
                time.sleep(0.05)
            return cond()
        said = lambda text: log.exists() and text in log.read_text()
        self.assertTrue(wait_for(lambda: sock.exists() and said("The first snip is read.")), (t / "panel.out").read_text())
        self.assertFalse(first.exists())                       # (Narrate's folder: removed once read)

        def send(request):
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
                c.connect(str(sock))
                c.sendall(json.dumps(request).encode())
        send({"image": str(yours / "snip.png"), "text": str(yours / "text.txt")})
        second = snip_folder(t, "snip-narrate-in-2", "The next snip is read too.")
        send({"image": str(second / "snip.png"), "text": str(second / "text.txt")})
        self.assertTrue(wait_for(lambda: said("The next snip is read too."), 10), log.read_text())
        self.assertNotIn(SECRET, log.read_text())
        self.assertTrue((yours / "snip.png").exists() and (yours / "text.txt").exists())
        # (nor does a request that isn't one at all close the panel, or one whose text is a FIFO,
        # which it waited on for good: the next snip is still read)
        send(["not", "a", "snip"])
        send({"image": 5, "text": None})
        fifo = snip_folder(t, "snip-narrate-in-fifo")
        (fifo / "text.txt").unlink()
        os.mkfifo(fifo / "text.txt")
        send({"image": str(fifo / "snip.png"), "text": str(fifo / "text.txt")})
        third = snip_folder(t, "snip-narrate-in-3", "And the one after.")
        send({"image": str(third / "snip.png"), "text": str(third / "text.txt")})
        self.assertTrue(wait_for(lambda: said("And the one after."), 10), (t / "panel.out").read_text())


if __name__ == "__main__":
    unittest.main()


class OneSelection(unittest.TestCase):
    """Arrow Pad's Snip pressed twice opened a second full-screen selection over the first: a
    selection now holds a lock for its life, and another start while it's held does nothing."""

    def test_a_second_selection_waits_for_the_first_to_end(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(fs, "RUN", Path(d)):
            code = ("import fcntl, sys, time; f = open(sys.argv[1], 'a'); "
                    "fcntl.flock(f, fcntl.LOCK_EX); print('held', flush=True); time.sleep(30)")
            first = subprocess.Popen([sys.executable, "-c", code, str(Path(d) / "frame-snip-select.lock")],
                                     stdout=subprocess.PIPE, text=True)
            self.addCleanup(first.kill)
            self.assertEqual(first.stdout.readline().strip(), "held")
            self.assertIsNone(fs.one_selection())             # (the first one's still open)
            first.kill()
            first.wait()
            lock = fs.one_selection()                          # (gone: the kernel let go)
            self.assertIsNotNone(lock)
            lock.close()


class ScreenTextOcr(unittest.TestCase):
    """Narrate found no text in a picture of the Frame Tweaks window: white text on dark buttons of
    different shades gave Tesseract nothing. A second pass reads a cleaned-up copy (for_ocr)."""

    @staticmethod
    def picture(bg, fg):
        from PyQt6.QtGui import QColor, QImage
        img = QImage(60, 30, QImage.Format.Format_RGB32)
        img.fill(QColor(bg))
        for x in range(20, 40):
            for y in range(10, 20):
                img.setPixelColor(x, y, QColor(fg))
        return img

    def test_light_text_on_dark_turns_black_on_white(self):
        out = fs.for_ocr(self.picture("#1b2026", "#f0f0f0"), scale=2)
        self.assertEqual((out.width(), out.height()), (120, 60))
        self.assertEqual(out.pixelColor(60, 30).lightness(), 0)        # (the text: black)
        self.assertEqual(out.pixelColor(5, 5).lightness(), 255)        # (the background: white)

    def test_dark_text_on_light_stays_black_on_white(self):
        out = fs.for_ocr(self.picture("#f4f4f4", "#101010"), scale=2)
        self.assertEqual(out.pixelColor(60, 30).lightness(), 0)
        self.assertEqual(out.pixelColor(5, 5).lightness(), 255)

    def test_the_cleaned_up_pass_counts_when_the_first_finds_little(self):
        img = self.picture("#1b2026", "#f0f0f0")
        calls = []
        def fake(image, path, psm):
            calls.append(psm)
            return "" if psm == "3" else "Dictate Hide Open Hide"
        with mock.patch.object(fs, "TESSERACT", sys.executable), mock.patch.object(fs, "tesseract", fake):
            self.assertEqual(fs.ocr(img), "Dictate Hide Open Hide")
        self.assertEqual(calls, ["3", "11"])

    def test_a_good_first_read_needs_no_second(self):
        text = "Plenty of ordinary text, read the first time round without help."
        with mock.patch.object(fs, "TESSERACT", sys.executable), \
             mock.patch.object(fs, "tesseract", lambda image, path, psm: text if psm == "3" else "x"):
            self.assertEqual(fs.ocr(self.picture("#ffffff", "#000000")), text)
