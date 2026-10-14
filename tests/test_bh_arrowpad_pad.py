"""Arrow Pad's keys (arrowpad.py) on a desktop pad built off-screen: a stand-in records what it
would type, its settings go to a scratch folder, and openvr can't be imported (no SteamVR)."""
import importlib.util
import json
import os
import shutil
import socket
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
PAD = ROOT / "packs/original/arrowpad"


class Keys:
    """Ydotool's interface, recording."""

    def __init__(self):
        self.sent = []

    def key(self, code, down):
        self.sent.append((code, down))

    def tap(self, *codes):
        self.sent.append(("tap",) + codes)

    def clear_stuck_modifiers(self):
        pass


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class PadTest(unittest.TestCase):
    LANGUAGE = "en"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "run").mkdir()
        env = {"QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen"), "FRAME_TWEAKS_KEYBOARD": "0",
               "FRAME_TWEAKS_LANGUAGE": self.LANGUAGE, "FRAME_TWEAKS_PREFERENCE_FILE": str(self.tmp / "language"),
               "FRAME_TWEAKS_ANNOUNCE_FILE": str(self.tmp / "run/language")}
        for p in (mock.patch.dict(os.environ, env), mock.patch.object(sys, "argv", ["arrowpad.py"]),
                  mock.patch.object(sys, "path", list(sys.path))):
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("DISPLAY", None)          # no --desktop/--vr and no :0: the desktop pad, here
        import PyQt6.QtNetwork  # noqa: F401     (imported before sys.modules is patched, so it stays)
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        p = mock.patch.dict(sys.modules, {"openvr": None,               # (the real one reaches SteamVR)
                                          "i18n": module("i18n", ROOT / "lib/i18n.py")})   # (not an installed copy)
        p.start()
        self.addCleanup(p.stop)
        self.ap = module("arrowpad", PAD / "arrowpad.py")
        self.ap.CONFIG, self.ap.Haptics = self.tmp / "arrowpad.json", None
        self.keys = Keys()
        self.pad = self.ap.ArrowPad(self.keys, None)

    def at(self, name):
        """(row, col, button) of a key on the layer showing."""
        return next((r, c, b) for r, c, b in self.pad.buttons if self.pad.name_at(r, c) == name)


class TakenBack(PadTest):
    def test_a_press_the_vr_panel_takes_back_lets_go_of_its_key(self):
        """A grab (or the dashboard closing) takes presses back with a release off the key, which
        isn't a click, so on_release never ran: a held ↓ or Bksp stayed down, repeating."""
        from PyQt6.QtCore import QEvent, Qt
        with mock.patch.dict(sys.modules, {"openvr": types.ModuleType("openvr")}):   # (a stand-in)
            v = module("vroverlay", PAD / "vroverlay.py")
        o = v.OverlayHost.__new__(v.OverlayHost)
        o.pad = self.pad
        held = [self.at(name)[2] for name in ("↓", "Ctrl", "Copy")]
        o.pressed = {}
        for laser, b in enumerate(held):
            o.send(b, QEvent.Type.MouseButtonPress, b.mapTo(self.pad, b.rect().center()), Qt.MouseButton.LeftButton)
            o.pressed[laser] = b
        self.assertEqual(self.keys.sent, [(108, True), (29, True)])     # ↓ and Ctrl down (Copy acts on release)
        o.cancel_presses()
        self.assertEqual(self.keys.sent[2:], [(108, False), (29, False)])
        self.assertEqual(self.pad.mod_state["Ctrl"], "off")             # not left latched either
        self.assertFalse(any(b.isDown() for b in held))
        o.cancel_presses()                                              # nothing more to let go of
        self.assertEqual(len(self.keys.sent), 4)

    def test_a_key_held_through_a_layer_switch_is_the_one_released(self):
        """Hold ↓ with one laser and tap Tools with the other: letting go of ↓ releases ↓ (it
        released what Tools has in its place, Redo: a Ctrl+Shift+Z, and ↓ stayed down)."""
        r, c, _ = self.at("↓")
        tr, tc, _ = self.at("Tools")
        self.pad.on_press(r, c)
        self.pad.on_press(tr, tc)
        self.pad.on_release(tr, tc)
        self.assertEqual(self.pad.layer, "tools")
        self.pad.on_release(r, c)
        self.assertEqual(self.keys.sent, [(108, True), (108, False)])


class Mic(PadTest):
    def test_without_dictation_it_says_so(self):
        """🎤 with Dictation not installed: a notification (starting the missing program raised,
        and an error inside a button's handler aborts the pad)."""
        home, started = self.tmp / "home", []
        self.pad.layer = "tools"
        r, c, _ = self.at("🎤")
        with mock.patch.object(self.ap.Path, "home", return_value=home), \
                mock.patch.object(self.ap.subprocess, "Popen", lambda cmd, **kw: started.append(cmd)):
            self.pad.on_press(r, c)
            self.pad.on_release(r, c)
            self.assertEqual(started[-1][0], "notify-send")
            (home / ".local/bin").mkdir(parents=True)
            (home / ".local/bin/dictate").touch()
            self.pad.on_press(r, c)
            self.pad.on_release(r, c)
            self.assertEqual(started[-1], [str(home / ".local/bin/dictate")])


class Scale(PadTest):
    def test_scale_given_beats_the_saved_size(self):
        """arrowpad --scale 1.5 (or ARROWPAD_SCALE): bigger keys even once a size was saved."""
        self.ap.CONFIG.write_text(json.dumps({"scale": 0.8}))
        self.assertEqual(self.ap.ArrowPad(Keys(), 1.5).scale, 1.5)
        self.assertEqual(self.ap.ArrowPad(Keys(), None).scale, 0.8)      # not given: the saved size


class Restart(PadTest):
    def test_typing_goes_on_after_ydotoold_restarts(self):
        """ydotool's ▶ Restart makes a new socket: the pad's still pointed at the old one, and the
        next key raised (aborting the pad). It connects again; while ydotoold is down, keys are lost."""
        path = f"\0arrowpad-test-{os.getpid()}-{id(self)}"                # (abstract: no file)
        size = struct.calcsize("llHHi")

        def ydotoold():
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            s.bind(path)
            s.settimeout(2)
            return s
        old = ydotoold()
        yd = self.ap.Ydotool(path)
        self.addCleanup(lambda: yd.sock.close())
        yd.key(30, True)
        self.assertEqual(struct.unpack("llHHi", old.recv(64))[2:], (1, 30, 1))
        old.close()
        new = ydotoold()                                                # restarted
        self.addCleanup(new.close)
        yd.key(30, False)
        self.assertEqual(struct.unpack("llHHi", new.recv(64))[2:], (1, 30, 0))
        self.assertEqual(len(new.recv(64)), size)                       # (and its EV_SYN)
        new.close()
        yd.key(30, True)                                                # ydotoold down: no error


class Legends(PadTest):
    LANGUAGE = "de"

    def test_a_language_without_a_translation_gets_its_keyboards_legends(self):
        """German (no de.po yet): the legends printed on German keyboards (SEED_LEGENDS), as the
        README says; without a catalogue they were English."""
        self.assertEqual([self.pad.label(k) for k in ("Del", "Home", "PgUp", "Ctrl", "Esc")],
                         ["Entf", "Pos1", "Bild↑", "Strg", "Esc"])


class EnglishLegends(PadTest):
    def test_english(self):
        self.assertEqual([self.pad.label(k) for k in ("Del", "Home", "Ctrl")], ["Del", "Home", "Ctrl"])


if __name__ == "__main__":
    unittest.main()
