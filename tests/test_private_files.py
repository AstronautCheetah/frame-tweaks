"""What you said or pressed is readable by you alone (mode 600), not only because of the folder
it's in (a home folder or runtime folder that's yours alone): Dictation's history (an older one
too, at the next dictation or reinstall), its log and its recordings; Arrow Pad's input log (a
new one after it rotates too, and the one before) and the notes under its VR panel, made so
before anything is written in them. In a throwaway home, with stand-ins: nothing real records,
transcribes, types or reaches SteamVR."""
import os
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script, sandbox_env, stub  # noqa: E402
DICTATION = ROOT / "packs/core/dictation"


def mode(path):
    return stat.S_IMODE(Path(path).stat().st_mode)


class Dictation(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "home"
        self.run_dir = self.tmp / "run"
        self.log = self.tmp / "log"
        self.log.write_text("")
        self.history = self.home / ".local/share/dictation-history.txt"
        self.history.parent.mkdir(parents=True)

    def dictate_once(self):
        """One dictation, started and stopped, with a copy of dictate whose runtime folder is in
        the throwaway home (pw-record writes its file, then records until it's stopped)."""
        src = (DICTATION / "dictate").read_text()
        self.assertIn("RUN=/run/user/$(id -u)\n", src)
        script = self.tmp / "dictate"
        script.write_text(src.replace("RUN=/run/user/$(id -u)\n", f"RUN={self.run_dir}\n"))     # (not the real one)
        bin_ = self.home / ".local/bin"           # first on dictate's PATH
        for name, body in (("pw-record", 'for f; do :; done; echo RIFF > "$f"; exec sleep 30 >/dev/null 2>&1'),
                           ("pw-play", "exit 0"), ("ffprobe", "echo 1.5"),
                           ("ffmpeg", 'echo "[Parsed_volumedetect_0] max_volume: -12.0 dB" >&2'),
                           ("whisper-cli", "echo 'My PIN is 1234.'"), ("wl-copy", "cat > /dev/null"),
                           ("ydotool", "exit 0"), ("notify-send", f'echo "notify $*" >> {self.log}')):
            stub(bin_, name, body)
        env = sandbox_env(self.home)
        for _ in ("start", "stop"):
            r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            time.sleep(0.8)                       # (a second press within 0.7 s is ignored)
        for _ in range(100):                      # (the stop transcribes in the background)
            if "Copied to clipboard" in self.log.read_text():
                break
            time.sleep(0.1)
        self.assertIn("My PIN is 1234.", self.history.read_text())

    def test_history_log_and_recordings_are_yours_only(self):
        self.dictate_once()
        state = self.run_dir / "dictate"
        self.assertEqual(mode(self.history), 0o600)
        self.assertEqual(mode(state / "dictate.log"), 0o600)
        self.assertIn("My PIN is 1234.", (state / "dictate.log").read_text())
        self.assertEqual(mode(state / "last.wav"), 0o600)
        self.assertEqual(mode(state), 0o700)

    def test_an_older_history_is_made_yours_only(self):
        """Older versions wrote it readable by everyone (0644): it's made 600 at the next
        dictation, and at the next install (an update)."""
        self.history.write_text("2026-01-01 10:00:00\tSomething said before.\n")
        self.history.chmod(0o644)
        (self.run_dir / "dictate").mkdir(parents=True)
        (self.run_dir / "dictate").chmod(0o755)
        self.dictate_once()
        self.assertEqual(mode(self.history), 0o600)
        self.assertEqual(mode(self.run_dir / "dictate"), 0o700)
        self.assertIn("Something said before.", self.history.read_text())

    def test_install_makes_an_older_history_yours_only(self):
        self.history.write_text("2026-01-01 10:00:00\tSomething said before.\n")
        self.history.chmod(0o644)
        src = (DICTATION / "install.sh").read_text()
        tail = src[src.index("# Your dictation history"):src.index('say "$(t "Done.')]   # (its last steps only)
        script = self.tmp / "install-tail.sh"
        script.write_text(f'source {ROOT / "lib/common.sh"}\n{tail}')
        r = subprocess.run(["bash", str(script)], env=sandbox_env(self.home), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(mode(self.history), 0o600)


class ArrowPadOverlay(unittest.TestCase):
    """vroverlay.py's input log and note pictures, with a stand-in for openvr and the folder they
    go in (TEX_DIR, the runtime folder) a throwaway one."""
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        with mock.patch.dict(sys.modules, {"openvr": types.ModuleType("openvr")}):
            cls.v = load_script(ROOT / "packs/core/arrowpad/vroverlay.py", "vroverlay_private")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        p = mock.patch.object(self.v, "TEX_DIR", str(self.dir))
        p.start()
        self.addCleanup(p.stop)
        self.o = self.v.OverlayHost.__new__(self.v.OverlayHost)
        self.o.INPUT_LOG = str(self.dir / "arrowpad-input.log")

    def test_the_input_log_is_yours_only(self):
        self.o.log_input("down overlay 0 on key 'Ctrl'")
        self.assertEqual(mode(self.o.INPUT_LOG), 0o600)
        Path(self.o.INPUT_LOG).chmod(0o644)                     # (an older version's)
        self.o.log_input("up   overlay 0 on key 'Ctrl'")
        self.assertEqual(mode(self.o.INPUT_LOG), 0o600)
        Path(self.o.INPUT_LOG).write_text("x" * 300_000)        # (past its size: a new one starts)
        self.o.log_input("down overlay 0 on key 'Esc'")
        self.assertTrue(Path(self.o.INPUT_LOG + ".1").exists())
        self.assertEqual(mode(self.o.INPUT_LOG), 0o600)
        self.assertIn("'Esc'", Path(self.o.INPUT_LOG).read_text())

    def test_the_input_log_is_made_yours_only_before_its_first_line(self):
        """(Not written readable by everyone, then changed: os.chmod does nothing here.) And the
        one before it (.1), an older Arrow Pad's readable by everyone, is made yours only too."""
        with mock.patch.object(self.v.os, "chmod", lambda *a, **k: None):
            self.o.log_input("down overlay 0 on key 'Ctrl'")
        self.assertEqual(mode(self.o.INPUT_LOG), 0o600)
        Path(self.o.INPUT_LOG + ".1").write_text("older presses\n")
        Path(self.o.INPUT_LOG + ".1").chmod(0o644)
        self.o.log_input("up   overlay 0 on key 'Ctrl'")
        self.assertEqual(mode(self.o.INPUT_LOG + ".1"), 0o600)

    def test_a_notes_picture_is_yours_only(self):
        """(Made so before it's written: os.chmod does nothing here.)"""
        logged = []
        self.o.log_input = logged.append
        self.o.ov = types.SimpleNamespace(createOverlay=lambda key, name: 7, setOverlaySortOrder=lambda h, n: None,
                                          setOverlayWidthInMeters=lambda h, m: None,
                                          setOverlayFromFile=lambda h, p: None, showOverlay=lambda h: None)
        self.o.place_note = lambda: None
        with mock.patch.object(self.v.os, "chmod", lambda *a, **k: None):
            self.o.show_note("Desktop mode has taken all input.")
        self.assertEqual(logged, [])
        notes = list(self.dir.glob("arrowpad-note-*.png"))
        self.assertEqual(len(notes), 1)
        self.assertEqual(mode(notes[0]), 0o600)
        from PyQt6.QtGui import QImage
        self.assertFalse(QImage(str(notes[0])).isNull())          # (a picture, written into the file made first)


if __name__ == "__main__":
    unittest.main()
