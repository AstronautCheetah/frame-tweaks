"""Screen snip's X clipboard helpers (frame-snip --x-clipboard, the owner Copy starts without
desktop mode, and --x-paste, the reader Narrate's Paste starts) start without PyQt6 or the shared
modules: the caller gives the owner 3 s to say it holds the clipboard and Paste 6 s in all, and
those imports alone took up to 6.4 s on a busy machine, so a loaded Frame said "Couldn't read the
clipboard." or "Couldn't copy" with nothing wrong. Here they're made unimportable and the helpers
still do their job: refuse a bad display, take their folder, and, where Xvfb is installed, own a
clipboard and read it back."""
import ctypes.util
import os
import select
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import helpers  # noqa: E402,F401  (imported for its side effects: English, as for every test)
SNIP = ROOT / "packs/core/snip/frame-snip"
BLOCKED = ("PyQt6", "i18n", "ftconf", "vrkit", "needs")


class Blocked(unittest.TestCase):
    """frame-snip run with PyQt6 and the shared modules unimportable."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        block = self.tmp / "block"
        block.mkdir()
        for name in BLOCKED:                    # (first on the path: an import of any of them fails)
            (block / name).mkdir()
            (block / name / "__init__.py").write_text(f"raise ImportError('{name} is blocked here')\n")
        self.env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.tmp), "LANG": "C.UTF-8",
                    "TMPDIR": str(self.tmp), "PYTHONPATH": str(block), "FRAME_TWEAKS_PYLIB": str(block)}

    def run_snip(self, *args, **kw):
        r = subprocess.run([sys.executable, str(SNIP), *args], env=self.env, capture_output=True, timeout=60,
                           stdin=subprocess.DEVNULL, **kw)
        self.assertNotIn(b"Traceback", r.stderr, r.stderr.decode(errors="replace"))
        return r

    def clip_folder(self, blobs):
        d = Path(tempfile.mkdtemp(prefix="snip-clip-", dir=self.tmp))
        for name, data in blobs.items():
            (d / name).write_bytes(data)
        return d


class Helpers(Blocked):
    def test_the_reader_refuses_a_bad_display_itself(self):
        r = self.run_snip("--x-paste", "remote:0")
        self.assertEqual(r.returncode, 1)
        self.assertIn(b"not an X display", r.stderr)

    def test_the_owner_refuses_a_bad_display_itself(self):
        d = self.clip_folder({"clip.txt": b"hi"})
        r = self.run_snip("--x-clipboard", str(d), "remote:0")
        self.assertEqual(r.returncode, 1)
        self.assertIn(b"not an X display", r.stderr)
        self.assertTrue(d.exists())             # (refused before reading or removing it)

    @unittest.skipUnless(ctypes.util.find_library("X11"), "needs libX11")
    def test_the_reader_answers_for_a_display_that_isnt_there(self):
        r = self.run_snip("--x-paste", ":987")
        self.assertEqual((r.returncode, r.stdout), (0, b"failed\n"))

    @unittest.skipUnless(ctypes.util.find_library("X11"), "needs libX11")
    def test_the_owner_takes_its_folder_then_finds_no_display(self):
        d = self.clip_folder({"clip.txt": b"hi"})
        r = self.run_snip("--x-clipboard", str(d), ":987")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(d.exists())            # (read and removed: it got past the imports to its own work)


@unittest.skipUnless(shutil.which("Xvfb") and sys.platform.startswith("linux"), "needs Xvfb")
class HelpersOnX(Blocked):
    """The owner says it's ready on its pipe and the reader reads what it offers, on a private
    Xvfb display, with PyQt6 and the shared modules still unimportable."""

    def setUp(self):
        super().setUp()
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

    def own(self, blobs):
        """Start the owner as hand_to_clipboard_owner does; True once its ready byte came."""
        r, w = os.pipe()
        owner = subprocess.Popen([sys.executable, str(SNIP), "--x-clipboard", str(self.clip_folder(blobs)),
                                  self.display], env=dict(self.env, FRAME_SNIP_READY_FD=str(w)), pass_fds=(w,),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.close(w)
        self.addCleanup(lambda: (owner.kill(), owner.wait(10), owner.stderr.close()))
        try:
            # (30 s: what's tested is that it gets there without the blocked imports, not how fast)
            ready, _w, _x = select.select([r], [], [], 30)
            ok = bool(ready) and os.read(r, 1) == b"1"
        finally:
            os.close(r)
        if not ok and owner.poll() is not None:
            self.fail(f"the owner ended ({owner.returncode}): " + owner.stderr.read().decode(errors="replace")[-2000:])
        return ok

    def test_text_copied_is_read_back(self):
        self.assertTrue(self.own({"clip.txt": "Grüße aus VR".encode()}))
        r = self.run_snip("--x-paste", self.display)
        self.assertEqual((r.returncode, r.stdout), (0, "text\nGrüße aus VR".encode()))

    def test_nothing_copied(self):
        r = self.run_snip("--x-paste", self.display)
        self.assertEqual((r.returncode, r.stdout), (0, b"empty\n"))


if __name__ == "__main__":
    unittest.main()
