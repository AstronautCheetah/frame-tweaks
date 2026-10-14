"""Screen snip's narration (frame-snip), offline: stand-ins for Piper and pw-play (nothing is
spoken), a throwaway home. "Read it again" after the end, a new speed while paused, a paste whose
clipboard owner doesn't answer, the ⚙ view following a new language, and an open VR panel (with a
stand-in openvr) reading the next snip at the speed set under Narrate."""
import importlib.machinery
import importlib.util
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
SNIP = ROOT / "packs/original/snip/frame-snip"
HOME = tempfile.TemporaryDirectory()       # (where the module's settings and Speech engine paths point)
TWO = ("The first sentence is long enough to be read on its own. "
       "The second sentence is long enough to be read on its own too.")
THREE = TWO + " And a third one follows them, just as long as the others."


def load():
    # --narrate: the panel's offscreen platform, never the Steam session's display; no i18n: English
    with mock.patch.object(sys, "argv", ["frame-snip", "--narrate"]), mock.patch.dict(sys.modules, {"i18n": None}), \
            mock.patch.dict(os.environ, {"HOME": HOME.name}):
        loader = importlib.machinery.SourceFileLoader("frame_snip", str(SNIP))
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("frame_snip", loader))
        loader.exec_module(mod)
    sys.path.remove(str(Path(HOME.name) / ".local/share/frame-tweaks/i18n"))
    return mod


fs = load()


def stub(path, body):
    path.write_text(f"#!/bin/bash\n{body}\n")
    path.chmod(0o755)


class Narration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        stubs = self.tmp / "stubs"
        stubs.mkdir()
        self.log = self.tmp / "log"
        self.log.write_text("")
        # Piper writes the file it's asked for; pw-play "plays" for a moment. PATH has only these.
        stub(stubs / "piper", 'while [ $# -gt 0 ]; do [ "$1" = --output_file ] && out=$2; shift; done\n'
                              f'/bin/cat > "$out"; echo "synth $out" >> {self.log}')
        stub(stubs / "pw-play", f'echo "play $1" >> {self.log}; exec /bin/sleep 0.3')
        for p in (mock.patch.dict(os.environ, {"PATH": str(stubs)}), mock.patch.object(fs, "PIPER", stubs / "piper"),
                  mock.patch.object(tempfile, "tempdir", str(self.tmp))):        # (its sound files go here)
            p.start()
            self.addCleanup(p.stop)

    def window(self, text):
        from PyQt6.QtGui import QImage
        w = fs.NarrationWindow(QImage(20, 20, QImage.Format.Format_RGB32), text, 1.0)
        self.addCleanup(lambda: w.narrator.cleanup())
        return w

    def wait(self, cond, seconds=10):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.app.processEvents()
            if cond():
                return True
            time.sleep(0.01)
        return False

    def played(self):
        return [l for l in self.log.read_text().splitlines() if l.startswith("play ")]

    def test_read_it_again_after_the_end_reads_again(self):
        w = self.window(TWO)
        self.assertTrue(self.wait(lambda: w.state.text() == "Finished."), w.state.text())
        before = len(self.played())
        w.stop_or_again()                                  # the button now offers "Read it again"
        self.assertTrue(self.wait(lambda: len(self.played()) > before), w.state.text())
        self.assertNotEqual(w.state.text(), "Stopped.")

    def test_a_new_speed_while_paused_carries_on_reading(self):
        w = self.window(THREE)
        self.assertTrue(self.wait(lambda: self.played()))
        w.pause_or_resume()                                # Pause, mid-sentence
        self.wait(lambda: False, 0.4)
        w.step(1)                                          # +: 1.25×, which also ends the pause
        self.assertTrue(self.wait(lambda: any(l.endswith("-1.25.wav") for l in self.played())),
                        self.log.read_text())
        self.assertFalse(w.narrator.paused)
        self.assertEqual(w.state.text(), "Reading aloud: part 1 of 3")

    def test_a_clipboard_that_doesnt_answer_is_no_text(self):
        w = self.window(TWO)
        with mock.patch.object(fs, "nested_wayland", lambda: "/nonexistent/wayland-0"), \
                mock.patch.object(fs, "wl_tool", lambda name: "/bin/true"), \
                mock.patch.object(fs.subprocess, "run", side_effect=subprocess.TimeoutExpired("wl-paste", 5)):
            self.assertIsNone(fs.from_clipboard())
            w.paste_text()                                 # (an exception here would abort the panel)
        self.assertEqual(w.state.text(), "The clipboard has no text.")

    def test_the_settings_view_follows_a_new_language(self):
        from PyQt6.QtWidgets import QLabel, QPushButton
        view = fs.SpeechConfig(lambda: None)
        de = {"Narrate with": "Vorlesen mit", "Piper: natural": "Piper: natürlich", "Language": "Sprache"}
        with mock.patch.object(fs, "_", lambda text: de.get(text, text)):
            fs.retranslate_tips(view)
        shown = {w.text() for w in view.findChildren(QLabel) + view.findChildren(QPushButton)}
        self.assertLessEqual(set(de.values()), shown)


# A stand-in for pyopenvr: every call succeeds, and there's no dashboard and no controller.
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


class OpenPanel(unittest.TestCase):
    def test_a_new_snip_is_read_at_the_speed_set_under_narrate(self):
        """The panel is open; a snip is narrated after its speed was set to 1.5× under Narrate (the
        snip window saves it): the panel reads it at 1.5×, not at the speed it had."""
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
        log = t / "log"
        stub(speech / "piper/piper", 'args="$*"\n'
                                     'while [ $# -gt 0 ]; do [ "$1" = --output_file ] && out=$2; shift; done\n'
                                     f'/bin/cat > "$out"; echo "synth $args" >> {log}')
        (speech / "voice.onnx").write_text("")
        stub(stubs / "pw-play", "exec /bin/sleep 0.2")
        (vr / "openvr.py").write_text(FAKE_OPENVR)
        settings = home / ".config/frame-tweaks/snip.json"
        settings.write_text(json.dumps({"speed": 1.0}))

        def snip(n):
            from PyQt6.QtGui import QImage
            d = t / f"snip{n}"
            d.mkdir()
            QImage(20, 20, QImage.Format.Format_RGB32).save(str(d / "snip.png"))
            (d / "text.txt").write_text(TWO)
            return str(d / "snip.png"), str(d / "text.txt")
        image, text = snip(1)
        boot = (f"import runpy, sys\nsys.path.insert(0, {str(vr)!r})\nimport openvr\n"
                f"assert openvr.__file__.startswith({str(vr)!r}), openvr.__file__   # (never the real one)\n"
                f"sys.argv = ['frame-snip', '--narrate', {image!r}, {text!r}]\n"
                f"runpy.run_path({str(SNIP)!r}, run_name='__main__')\n")
        import PyQt6
        # (this PyQt6 wherever it's installed: pip's --user install, as on CI, is found through HOME,
        # and the panel's is a throwaway one)
        env = {"HOME": str(home), "PATH": str(stubs), "TMPDIR": str(t), "QT_QPA_PLATFORM": "offscreen",
               "FRAME_TWEAKS_LANGUAGE": "en", "PYTHONPATH": str(Path(PyQt6.__file__).resolve().parent.parent)}
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
        said = lambda scale: log.exists() and f"--length_scale {scale}" in log.read_text()
        self.assertTrue(wait_for(lambda: sock.exists() and said("1.000")), (t / "panel.out").read_text())
        settings.write_text(json.dumps({"speed": 1.5}))      # − / + under Narrate, then Narrate
        image, text = snip(2)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
            c.connect(str(sock))
            c.sendall(json.dumps({"image": image, "text": text}).encode())
        self.assertTrue(wait_for(lambda: said("0.667"), 10), log.read_text())


if __name__ == "__main__":
    unittest.main()
