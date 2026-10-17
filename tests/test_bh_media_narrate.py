"""Screen snip's narration (frame-snip), offline: stand-ins for Piper and pw-play (nothing is
spoken), a throwaway home. "Read it again" after the end, a new speed while paused, Previous /
Next (playing and paused, up to the first and last part), a Pause as the last part ends, a
Speech engine that fails (no sound file, or it doesn't start), a paste whose clipboard owner
doesn't answer, the ⚙ view following a new language, and the VR panel (with a stand-in openvr):
an open one reading the next snip at the speed set under Narrate, and closing cleanly when its
OpenVR calls fail."""
import io
import json
import os
import signal
import socket
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
from helpers import load_script, stub  # noqa: E402
SNIP = ROOT / "packs/core/snip/frame-snip"
HOME = tempfile.TemporaryDirectory()       # (where the module's settings and Speech engine paths point)
TWO = ("The first sentence is long enough to be read on its own. "
       "The second sentence is long enough to be read on its own too.")
THREE = TWO + " And a third one follows them, just as long as the others."


def load():
    # --narrate: the panel's offscreen platform, never the Steam session's display; no i18n: English
    with mock.patch.object(sys, "argv", ["frame-snip", "--narrate"]), mock.patch.dict(sys.modules, {"i18n": None}), \
            mock.patch.dict(os.environ, {"HOME": HOME.name}):
        mod = load_script(SNIP, "frame_snip")
    sys.path.remove(os.environ.get("FRAME_TWEAKS_PYLIB") or str(Path(HOME.name) / ".local/share/frame-tweaks/i18n"))
    return mod


fs = load()


def stub_at(path, body):
    stub(path.parent, path.name, body)


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
        stub_at(stubs / "piper", 'while [ $# -gt 0 ]; do [ "$1" = --output_file ] && out=$2; shift; done\n'
                              f'/bin/cat > "$out"; echo "synth $out" >> {self.log}')
        # (pw-play --volume V FILE: the file is the last argument)
        stub_at(stubs / "pw-play", f'echo "play ${{@: -1}}" >> {self.log}; echo "volume $2" >> {self.log}.volume; exec /bin/sleep 0.3')
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

    def slow_player(self):
        """A pw-play that plays until it's stopped (so the narration stays on its part), and logs its
        process id (exec: the sleep's)."""
        stub_at(self.tmp / "stubs/pw-play", f'echo "play ${{@: -1}} $$" >> {self.log}; exec /bin/sleep 60')

    def playing(self):
        """[(part, process id)] for each pw-play started, in order (slow_player)."""
        return [(int(Path(wav).name.split("-")[0]), int(pid)) for _, wav, pid in map(str.split, self.played())]

    @staticmethod
    def alive(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    @staticmethod
    def proc_state(pid):
        """A process's state letter (Z: ended, not yet reaped), or None once it's gone."""
        try:
            return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        except (OSError, IndexError):
            return None

    def processes(self, w):
        """The narrator's QProcesses still around, once what was let go of is deleted."""
        from PyQt6.QtCore import QCoreApplication, QEvent, QProcess
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return w.narrator.findChildren(QProcess)

    def skips(self, w):
        return w.previous_button.isEnabled(), w.next_button.isEnabled()

    def test_previous_and_next_move_a_part_up_to_the_first_and_last(self):
        self.slow_player()
        w = self.window(THREE)
        self.assertEqual(self.skips(w), (False, False))                  # (nothing to move through yet)
        self.assertTrue(self.wait(lambda: self.playing()), w.state.text())
        self.assertEqual(w.state.text(), "Reading aloud: part 1 of 3")
        self.assertEqual(self.skips(w), (False, True))                   # Previous: none before the first
        for button, part, skips in ((w.next_button, 1, (True, True)), (w.next_button, 2, (True, False)),
                                    (w.previous_button, 1, (True, True)), (w.previous_button, 0, (False, True))):
            before = self.playing()
            button.click()
            self.assertEqual(w.narrator.i, part)
            self.assertTrue(self.wait(lambda: len(self.playing()) > len(before)), self.log.read_text())
            self.assertEqual(self.playing()[-1][0], part)                # that part, from its start
            self.assertFalse(self.alive(before[-1][1]), "the part before it is still playing")
            self.assertEqual(w.state.text(), f"Reading aloud: part {part + 1} of 3")
            self.assertEqual(self.skips(w), skips)
            self.assertNotIn(before[-1][1], [p.processId() for p in self.processes(w)])
        w.narrator.skip(-1)                                              # (Previous is greyed out here)
        self.assertEqual(w.narrator.i, 0)
        self.wait(lambda: False, 0.3)
        self.assertEqual(len(self.playing()), 5)
        self.assertTrue(self.alive(self.playing()[-1][1]))               # still reading the first part
        w.stop_or_again()                                                # Stop: nothing to move through
        self.assertEqual(self.skips(w), (False, False))
        self.assertFalse(any(self.alive(pid) for _, pid in self.playing()))
        self.assertEqual(self.processes(w), [])

    def test_previous_and_next_while_paused_stay_paused_there(self):
        self.slow_player()
        w = self.window(THREE)
        self.assertTrue(self.wait(lambda: self.playing() and 1 in w.narrator.wavs and not w.narrator.synth),
                        w.state.text())                                  # (the next part prepared, as it plays)
        w.pause_or_resume()                                              # Pause, mid-sentence
        first = self.playing()[0][1]
        w.next_button.click()
        self.assertTrue(w.narrator.paused)
        self.assertEqual(w.narrator.i, 1)
        self.assertEqual(w.state.text(), "Paused: part 2 of 3")
        self.assertFalse(self.alive(first), "the paused part's player is still there")
        w.next_button.click()
        self.assertEqual((w.narrator.i, self.skips(w)), (2, (True, False)))
        self.assertEqual(w.state.text(), "Paused: part 3 of 3")
        self.assertTrue(self.wait(lambda: 2 in w.narrator.wavs))          # prepared while paused (only
        w.previous_button.click()                                        # the next one was, playing)
        self.assertEqual((w.narrator.i, self.skips(w)), (1, (True, True)))
        self.assertEqual(w.state.text(), "Paused: part 2 of 3")
        self.wait(lambda: False, 0.3)
        self.assertEqual(len(self.playing()), 1, "it read while paused")
        w.pause_or_resume()                                              # Resume: from part 2's start
        self.assertTrue(self.wait(lambda: len(self.playing()) == 2), self.log.read_text())
        self.assertEqual(self.playing()[-1][0], 1)
        self.assertFalse(w.narrator.paused)
        self.assertEqual(w.state.text(), "Reading aloud: part 2 of 3")

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

    def test_volume_down_and_up(self):
        """Its own volume, in tenths, remembered: the next parts start at it, and the part
        playing changes at once (pactl, by the stream's name: the part's file)."""
        stubs = self.tmp / "stubs"
        stub_at(stubs / "pactl", 'echo "pactl $*" >> ' + f"{self.log}.pactl" + '\n'
                                  'if [ "$1" = -f ]; then printf \'[{"index": 7, "properties": {"media.name": "%s"}}]\' '
                                  '"$(/bin/cat ' + f"{self.tmp}/now" + ')"; fi')
        self.slow_player()
        stub_at(stubs / "pw-play", f'echo "play ${{@: -1}} $$" >> {self.log}; echo "volume $2" >> {self.log}.volume; '
                                   f'echo -n "${{@: -1}}" > {self.tmp}/now; exec /bin/sleep 60')
        with mock.patch.object(fs, "PACTL", str(stubs / "pactl")):
            w = self.window(THREE)
            self.assertEqual(w.volume, 1.0)
            self.assertFalse(w.louder.isEnabled())                        # (100%: as loud as it goes)
            self.assertTrue(self.wait(lambda: self.playing()))
            w.step_volume(-1)
            w.step_volume(-1)
            self.assertEqual(w.volume, 0.8)
            self.assertTrue(w.louder.isEnabled())
            self.assertTrue(self.wait(lambda: "set-sink-input-volume 7 0.80" in (self.tmp / "log.pactl").read_text()
                                      if (self.tmp / "log.pactl").exists() else False), self.log.read_text())
            self.assertEqual(fs.load_volume(), 0.8)                       # (remembered)
            w.narrator.skip(1)                                            # the next part starts at it
            self.assertTrue(self.wait(lambda: len(self.playing()) == 2))
        self.assertEqual(Path(f"{self.log}.volume").read_text().split("\n")[:2], ["volume 1.00", "volume 0.80"])
        for _ in range(12):
            w.step_volume(-1)
        self.assertEqual(w.volume, 0.1)
        self.assertFalse(w.quieter.isEnabled())
        fs.save_volume(1.0)

    def test_pause_as_the_last_part_ends_still_finishes(self):
        """Pause pressed after the last part's player ended, before Qt says so: it stayed
        "Paused." at the end, and Stop (still offered) read it all again. Now it finishes."""
        self.slow_player()
        w = self.window("The only sentence, long enough to be read on its own.")
        self.assertTrue(self.wait(lambda: self.playing()), w.state.text())
        pid = self.playing()[-1][1]
        os.kill(pid, signal.SIGKILL)               # it ends; no events handled meanwhile: Qt doesn't know
        end = time.monotonic() + 5
        while self.proc_state(pid) not in ("Z", None) and time.monotonic() < end:
            time.sleep(0.01)
        if self.proc_state(pid) != "Z":
            self.skipTest("the player was reaped at once: Qt knows it ended")
        w.pause_or_resume()                        # Pause
        self.assertTrue(self.wait(lambda: w.state.text() == "Finished."), w.state.text())
        self.assertFalse(w.narrator.paused)
        self.assertEqual((w.toggle.toolTip(), w.pause_button.toolTip()), ("Read it again", "Pause"))
        before = len(self.played())
        w.stop_or_again()                          # Read it again
        self.assertTrue(self.wait(lambda: len(self.played()) > before), w.state.text())

    def test_a_speech_engine_that_makes_no_sound_is_tried_twice_then_stops(self):
        """Piper ends without its sound file (with an error, or without one): it was started
        again and again (143 times in 3 s), saying nothing. Now the part is tried once more, then
        it stops there and says why; Read it again tries again."""
        for code in (1, 0):
            with self.subTest(exit=code):
                self.log.write_text("")
                stub_at(self.tmp / "stubs/piper", f'echo synth >> {self.log}; exit {code}')
                w = self.window(TWO)
                self.assertTrue(self.wait(lambda: w.narrator.stopped, 3), self.log.read_text())
                self.wait(lambda: False, 0.3)
                self.assertEqual(self.log.read_text().count("synth"), 2)
                self.assertEqual(w.state.text(), "The Speech engine failed to read part 1.")
                self.assertEqual(w.toggle.toolTip(), "Read it again")
                self.assertFalse(w.pause_button.isEnabled())
        stub_at(self.tmp / "stubs/piper", 'while [ $# -gt 0 ]; do [ "$1" = --output_file ] && out=$2; shift; done\n'
                                         '/bin/cat > "$out"')
        w.stop_or_again()                          # Read it again (Piper works again)
        self.assertTrue(self.wait(lambda: self.played()), w.state.text())
        self.assertEqual(w.toggle.toolTip(), "Stop")

    def test_a_part_that_fails_stops_it_when_its_turn_comes(self):
        """The second part fails while the first plays: the first is read to its end, then it
        stops at the second, saying so."""
        stub_at(self.tmp / "stubs/piper", 'while [ $# -gt 0 ]; do [ "$1" = --output_file ] && out=$2; shift; done\n'
                                         f'text=$(/bin/cat); echo "synth $text" >> {self.log}\n'
                                         'case "$text" in *second*) exit 1 ;; esac; printf %s "$text" > "$out"')
        w = self.window(THREE)
        self.assertTrue(self.wait(lambda: w.narrator.stopped, 5), w.state.text())
        self.assertEqual(w.state.text(), "The Speech engine failed to read part 2.")
        self.assertEqual(len(self.played()), 1)                          # the first, to its end
        self.assertEqual(sum("second" in l for l in self.log.read_text().splitlines()), 2)

    def test_a_speech_engine_that_doesnt_start_says_so(self):
        """Piper missing (it can't start, so it never finishes): it said "Preparing…" for ever,
        and Read it again read nothing. Now it says so, and Read it again tries again."""
        with mock.patch.object(fs, "PIPER", self.tmp / "gone/piper"):
            w = self.window(TWO)
            self.assertTrue(self.wait(lambda: w.narrator.stopped, 3), w.state.text())
            self.assertEqual(w.state.text(), "The Speech engine didn't start: reinstall it in Frame Tweaks.")
            self.assertIsNone(w.narrator.synth)
        w.stop_or_again()                          # Read it again, with Piper back
        self.assertTrue(self.wait(lambda: self.played()), w.state.text())

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

    # ---- The VR panel's own overlay (NarrationOverlay), with a stand-in openvr (below) whose
    # calls start failing, as they would with SteamVR restarting under an open panel.
    def panel(self):
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QImage
        vr = types.ModuleType("openvr")
        exec(FAKE_OPENVR, vr.__dict__)
        # An exception that leaves a Qt slot goes to sys.excepthook: kept here (by default PyQt6
        # aborts the program on one, and the tests with it)
        self.escaped = []
        panels = tempfile.TemporaryDirectory()          # (its DashboardGrab files: not the real runtime folder's)
        self.addCleanup(panels.cleanup)
        self.panels = Path(panels.name)
        for p in (mock.patch.dict(sys.modules, {"openvr": vr}),
                  mock.patch.object(fs.vrkit.DashboardGrab, "PANELS", self.panels),
                  mock.patch.object(sys, "excepthook", lambda *e: self.escaped.append(e[1]))):
            p.start()
            self.addCleanup(p.stop)
        w = fs.NarrationWindow(QImage(20, 20, QImage.Format.Format_RGB32), TWO, 1.0, panel=True)
        self.addCleanup(lambda: w.narrator.cleanup())
        w.show()
        overlay = fs.NarrationOverlay(w)
        self.addCleanup(overlay.close)
        self.addCleanup(lambda: [t.stop() for t in overlay.findChildren(QTimer)])
        return w, overlay, vr._vr.VROverlay.return_value

    def test_an_openvr_error_in_its_timers_closes_it_cleanly(self):
        """An error leaving one of its timers ended the program at once (PyQt6 aborts), with the
        narration's files left behind. Now the panel closes as Close does."""
        def gone(*_):
            raise RuntimeError("SteamVR is gone")
        for call in ("pollNextOverlayEvent", "setOverlayFromFile"):     # (its events; its picture)
            with self.subTest(call=call):
                w, overlay, ov = self.panel()
                getattr(ov, call).side_effect = gone
                err = io.StringIO()
                with mock.patch.object(sys, "stderr", err):
                    self.wait(lambda: not w.isVisible(), 3)
                self.assertEqual(self.escaped, [])
                self.assertFalse(w.isVisible())
                self.assertTrue(w.narrator.stopped)
                self.assertFalse(w.narrator.dir.exists())
                self.assertIn("SteamVR is gone", err.getvalue())
                calls = len(ov.mock_calls)
                self.wait(lambda: False, 0.3)
                self.assertEqual(len(ov.mock_calls), calls)          # its timers stopped too
                overlay.close()
                self.assertFalse(overlay.tex_dir.exists())

    def test_with_the_controllers_hidden_it_slides_after_the_laser(self):
        """Steam's keyboard open: SteamVR hides the controllers from other programs (the stand-in
        has none either), and carrying the panel did nothing. It slides in its own plane after the
        laser instead, half the way each time (Arrow Pad's), with a note under it that goes a while
        after you let go."""
        from PyQt6.QtCore import QPoint
        w, overlay, ov = self.panel()
        overlay.poll_timer.stop()
        vr = sys.modules["openvr"]
        vr.VREvent_MouseMove, vr.VREvent_MouseButtonDown, vr.VREvent_MouseButtonUp, vr.VREvent_FocusLeave = 1, 2, 3, 4
        queue = []

        def next_event(_handle, ev):
            if not queue:
                return (False, None)
            t, at = queue.pop(0)
            ev.eventType, ev.trackedDeviceIndex = t, 1
            ev.data = types.SimpleNamespace(mouse=types.SimpleNamespace(x=at.x(), y=w.height() - at.y()))
            return (True, ev)
        vr.VREvent_t = lambda: types.SimpleNamespace()
        ov.pollNextOverlayEvent.side_effect = next_event
        empty = next(QPoint(x, y) for y in range(w.height() - 5, 5, -7) for x in range(5, w.width() - 5, 7)
                     if overlay.button_at(QPoint(x, y)) is None)
        before = [row[3] for row in overlay.pose]
        queue[:] = [(2, empty)]
        overlay.poll()
        self.assertIsNotNone(overlay.drag)
        self.assertIsNone(overlay.drag[1])                                  # (sliding, not carried)
        self.assertIsNotNone(overlay.note)
        self.assertIn(mock.call(overlay.key + ".note", "Screen snip"), ov.createOverlay.call_args_list)
        queue[:] = [(1, empty + QPoint(100, 0)), (1, empty + QPoint(100, 40))]
        overlay.poll()                                                     # (only the latest spot counts)
        moved = [overlay.pose[i][3] - before[i] for i in range(3)]
        k = 0.5 * overlay.M_PER_PX
        want = [k * (overlay.pose[i][0] * 100 - overlay.pose[i][1] * 40) for i in range(3)]
        for got, exp in zip(moved, want):
            self.assertAlmostEqual(got, exp)
        with mock.patch.object(overlay, "NOTE_LINGER_MS", 10):
            queue[:] = [(3, empty + QPoint(100, 40))]
            overlay.poll()
            self.assertIsNone(overlay.drag)
            self.assertTrue(self.wait(lambda: overlay.note is None, 2))
        ov.destroyOverlay.assert_called()
        self.assertEqual(self.escaped, [])

    def test_steamvrs_grab_bar_moves_it(self):
        """While Steam's keyboard is open, SteamVR's grab bar under the panel (the VR environment
        helper's panel-grab patch): held, the panel hides (a picture of it moves instead); let go,
        it's where the picture was, and remembers the spot."""
        w, overlay, ov = self.panel()
        overlay.poll_timer.stop()
        overlay.poll()
        said = json.loads((self.panels / f"{overlay.key}.json").read_text())
        self.assertEqual(said["w"], round(overlay.width_px * overlay.M_PER_PX, 4))
        self.assertTrue(said["picture"].endswith(".png"))
        grab = self.panels / f"{overlay.key}.grab.json"
        grab.write_text(json.dumps({"seq": 1, "state": "held"}))
        overlay.poll()
        self.assertTrue(overlay.dash_held)
        ov.hideOverlay.assert_any_call(overlay.h)
        t = {"x": 0.3, "y": 1.1, "z": -0.7}
        with mock.patch.object(overlay, "save_offset") as saved:
            grab.write_text(json.dumps({"seq": 2, "state": "dropped", "t": t, "r": said["r"]}))
            overlay.poll()
        self.assertFalse(overlay.dash_held)
        self.assertEqual([round(overlay.pose[i][3], 4) for i in range(3)], [0.3, 1.1, -0.7])
        saved.assert_called_once()
        ov.showOverlay.assert_called_with(overlay.h)
        overlay.close()
        self.assertFalse((self.panels / f"{overlay.key}.json").exists())


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
        stub_at(speech / "piper/piper", 'args="$*"\n'
                                     'while [ $# -gt 0 ]; do [ "$1" = --output_file ] && out=$2; shift; done\n'
                                     f'/bin/cat > "$out"; echo "synth $args" >> {log}')
        (speech / "voice.onnx").write_text("")
        stub_at(stubs / "pw-play", "exec /bin/sleep 0.2")
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
               "FRAME_TWEAKS_PYLIB": str(ROOT / "lib"),
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
