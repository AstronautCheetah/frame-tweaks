"""Arrow Pad's keys (arrowpad.py) on a desktop pad built off-screen: a stand-in records what it
would type, its settings go to a scratch folder, and openvr can't be imported (no SteamVR)."""
import importlib.util
import io
import itertools
import json
import os
import shutil
import signal
import socket
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
PAD = ROOT / "packs/core/arrowpad"


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


def layouts_compile():
    """libxkbcommon and XKB's layouts are here (SteamOS; CI's Ubuntu has them with Qt's libraries)."""
    try:
        module("xkb_check", ROOT / "lib/xkb.py").Keymap("fr")
        return True
    except OSError:
        return False


def mo(messages):
    """A gettext catalogue (.mo file's bytes) with these {msgid: msgstr} (UTF-8)."""
    messages = {"": "Content-Type: text/plain; charset=UTF-8\n", **messages}
    keys = sorted(messages)
    start, blob, tables = 28 + 16 * len(keys), b"", ([], [])
    for table, texts in zip(tables, (keys, [messages[k] for k in keys])):
        for s in texts:
            table.append(struct.pack("<2I", len(s.encode()), start + len(blob)))
            blob += s.encode() + b"\0"
    return (struct.pack("<7I", 0x950412de, 0, len(keys), 28, 28 + 8 * len(keys), 0, 0)
            + b"".join(tables[0]) + b"".join(tables[1]) + blob)


_sockets = itertools.count()


def ydotoold(test):
    """A stand-in for ydotoold, and a Ydotool (arrowpad.py's) talking to it."""
    path = f"\0arrowpad-test-{os.getpid()}-{next(_sockets)}"            # (abstract: no file)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    s.bind(path)
    s.setblocking(False)
    test.addCleanup(s.close)
    yd = test.ap.Ydotool(path)
    test.addCleanup(yd.sock.close)
    return s, yd


def received(s):
    """The key events (code, 1 down / 0 up) the stand-in has had since last asked."""
    out = []
    while True:
        try:
            _, _, kind, code, value = struct.unpack("llHHi", s.recv(64))
        except BlockingIOError:
            return out
        if kind == 1:
            out.append((code, value))


class PadTest(unittest.TestCase):
    LANGUAGE = "en"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "run").mkdir()
        env = {"QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen"), "FRAME_TWEAKS_KEYBOARD": "0",
               "FRAME_TWEAKS_LANGUAGE": self.LANGUAGE, "FRAME_TWEAKS_PREFERENCE_FILE": str(self.tmp / "language"),
               "FRAME_TWEAKS_ANNOUNCE_FILE": str(self.tmp / "run/language"),
               "FRAME_TWEAKS_PYLIB": str(ROOT / "lib"),            # (the repo's shared modules, not an installed copy)
               "XDG_CONFIG_HOME": str(self.tmp / "config")}         # (no kxkbrc: a US keyboard)
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

    def mouse(self, button, kind, on=True):
        """A mouse event as a pointer delivers it to a key: kind press, move or release, on the key
        or just off its edge (vroverlay.py sends the VR panel's the same way)."""
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication
        r = button.rect()
        pos = QPointF(r.center()) if on else QPointF(r.right() + 20, r.center().y())
        etype = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
                 "release": QEvent.Type.MouseButtonRelease}[kind]
        held = Qt.MouseButton.NoButton if kind == "release" else Qt.MouseButton.LeftButton
        QApplication.sendEvent(button, QMouseEvent(etype, pos, QPointF(button.mapToGlobal(pos.toPoint())),
                                                   Qt.MouseButton.LeftButton, held, Qt.KeyboardModifier.NoModifier))

    def tap(self, name, layer=None, wander=0, let_go_on=True):
        """Press the key, slide off its edge and back `wander` times, let go (on the key or off it)."""
        if layer and self.pad.layer != layer:
            self.pad.layer = layer
            self.pad.relabel()
        b = self.at(name)[2]
        self.mouse(b, "press")
        for _ in range(wander):
            self.mouse(b, "move", on=False)
            self.mouse(b, "move")
        if not let_go_on:
            self.mouse(b, "move", on=False)
        self.mouse(b, "release", on=let_go_on)


class LatchedModifiers(PadTest):
    """A modifier tapped (latched for the next key) or locked: the buttons that start something
    else let it go first."""
    def test_dictation_types_without_a_modifier_down(self):
        """Dictation types through the same ydotoold: Ctrl still down made every letter Ctrl+letter."""
        self.tap("Ctrl")                                    # latched: down
        self.tap("Alt")
        self.tap("Alt")                                     # locked
        seen = []
        with mock.patch.object(self.pad, "dictate", lambda: seen.append(list(self.keys.sent))):
            self.tap("🎤", layer="tools")
        self.assertIn((self.ap.KEY["Ctrl"], False), seen[0])
        self.assertIn((self.ap.KEY["Alt"], False), seen[0])
        self.assertEqual(self.pad.mod_state["Ctrl"], "off")
        self.assertEqual(self.pad.mod_state["Alt"], "off")

    def test_dictation_started_elsewhere_lets_them_go(self):
        """Dictation lets go of the modifiers on ydotoold's keyboard before it types, however it
        was started (its shortcut, the menu): the pad's go off with it, as it starts and as it ends
        (one latched meanwhile), so the pad doesn't show a Ctrl that isn't down. Alt and Super go
        up around F24 (alone, that'd be a tap: the launcher); one a laser holds stays."""
        state = ["idle"]
        self.pad.dictation_state = lambda: state[0]

        def dictation(now):
            self.keys.sent.clear()
            state[0] = now
            self.pad.refresh_mic()
            return self.keys.sent

        self.tap("Ctrl", layer="tools")                      # latched
        self.tap("Super")
        self.tap("Super")                                    # locked
        self.assertEqual(dictation("recording"), [(194, True), (29, False), (125, False), (194, False)])
        self.assertEqual(self.pad.mod_state, {"Ctrl": "off", "Alt": "off", "Super": "off"})
        self.tap("Ctrl")
        self.assertEqual(dictation("transcribing"), [])      # (going on: Ctrl+something meanwhile is yours)
        self.assertEqual(self.pad.mod_state["Ctrl"], "oneshot")
        self.assertEqual(dictation("idle"), [(29, False)])    # (it typed: Ctrl was let go)
        self.assertEqual(self.pad.mod_state["Ctrl"], "off")
        self.mouse(self.at("Alt")[2], "press")               # a laser holding Alt
        self.assertEqual(dictation("recording"), [])
        self.assertEqual(self.pad.mod_state["Alt"], "held")
        self.mouse(self.at("Alt")[2], "release")

    def test_snip_lets_a_latched_modifier_go(self):
        self.tap("Ctrl", layer="tools")
        seen = []
        with mock.patch.object(self.pad, "snip", lambda: seen.append(list(self.keys.sent))):
            self.tap("Snip", layer="tools")
        self.assertIn((self.ap.KEY["Ctrl"], False), seen[0])

    def test_the_launcher_with_super_latched(self):
        """Super latched is down already: letting it go is the tap (a second press was dropped,
        and Super was up while the pad showed it latched)."""
        self.tap("Super", layer="tools")
        self.keys.sent.clear()
        self.tap("Launcher", layer="tools")
        self.assertEqual(self.keys.sent, [(self.ap.KEY["Super"], False)])
        self.assertEqual(self.pad.mod_state["Super"], "off")
        self.keys.sent.clear()
        self.tap("Launcher", layer="tools")
        self.assertEqual(self.keys.sent, [("tap", self.ap.KEY["Super"])])


class SlideNote(PadTest):
    def test_the_note_is_drawn_and_wraps(self):
        """The note under the pad while it slides (Steam's keyboard open): its words fit, wrapped."""
        with mock.patch.dict(sys.modules, {"openvr": types.ModuleType("openvr")}):   # (a stand-in)
            v = module("vroverlay", PAD / "vroverlay.py")
        short, long = v.note_image("Slide"), v.note_image("While Steam's keyboard is open, Arrow Pad can only "
                                                          "slide. Close the keyboard to move it closer, further "
                                                          "away or turn it.")
        self.assertEqual((short.width(), long.width()), (v.NOTE_PX, v.NOTE_PX))
        self.assertGreater(long.height(), short.height() * 1.5)          # (more than one line)
        self.assertEqual(long.pixelColor(v.NOTE_PX // 2, 2).alpha(), 235)   # (the dark box, see-through a little)


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
        down = self.at("↓")[2]
        self.mouse(down, "press")
        self.tap("Tools")
        self.assertEqual(self.pad.layer, "tools")
        self.mouse(down, "release")
        self.assertEqual(self.keys.sent, [(108, True), (108, False)])


class Unstick(PadTest):
    """Unstick: a keyboard that lost a key's release (Bluetooth) still holds it for every app, and
    the pad's own presses can't let go of another device's key; a release written to that device
    does. Desktop mode's input grab (Right Ctrl) isn't a held key: Unstick says how to undo it."""
    def test_lets_go_of_keys_a_keyboard_holds(self):
        dev = self.tmp / "event7"                               # (a file stands in for the device node)
        dev.touch()
        with mock.patch.object(self.ap, "held_keys", return_value=[29, 14, 97]):
            got = self.ap.release_held_keys({str(dev): "Keyboard Craft Keyboard"})
        self.assertEqual(got, {"Keyboard Craft Keyboard": [29, 14]})       # (never Right Ctrl: the grab key)
        size = struct.calcsize("llHHi")
        data = dev.read_bytes()
        events = [struct.unpack("llHHi", data[i:i + size])[2:] for i in range(0, len(data), size)]
        self.assertEqual(events, [(1, 29, 0), (1, 14, 0), (0, 0, 0)])     # releases, then a report
        with mock.patch.object(self.ap, "held_keys", return_value=[]):
            self.assertEqual(self.ap.release_held_keys({str(dev): "Keyboard Craft Keyboard"}), {})

    def test_only_keyboards_and_mice(self):
        devices = "\n\n".join((
            'N: Name="pmic_pwrkey"\nH: Handlers=kbd event0\nB: KEY=10000000000000 0',
            'N: Name="Keyboard Craft Keyboard"\nH: Handlers=sysrq kbd leds event7\n'
            'B: KEY=33eff 0 0 483ffff17aff32d bfd4444600000000 1 130ff38b17c007 ffe77bfad9415fff febeffdfffefffff '
            'fffffffffffffffe',
            'N: Name="Keyboard Craft Mouse"\nH: Handlers=mouse0 event8\nB: KEY=1f0000 0 0 0 0',
            'N: Name="Microsoft X-Box 360 pad 0"\nH: Handlers=event5 js0\nB: KEY=7cdb000000000000 0 0 0 0'))
        self.assertEqual(self.ap.keyboards(devices), {"/dev/input/event7": "Keyboard Craft Keyboard",
                                                      "/dev/input/event8": "Keyboard Craft Mouse"})

    def unstick(self, held, grabbed):
        """Unstick with these held keys and these answers to "is desktop mode's grab on?"; the
        message it shows, after its check (600 ms)."""
        from PyQt6.QtTest import QTest
        self.ap.UNSTICK_LOG = self.tmp / "unstick.log"
        with mock.patch.object(self.ap, "release_held_keys", return_value=held), \
                mock.patch.object(self.ap, "desktop_grabbed", side_effect=grabbed), \
                mock.patch.object(self.ap.subprocess, "Popen") as popen:
            self.pad.unstick()
            for _ in range(500):                # (its check after 600 ms: later on a busy machine)
                if popen.called:
                    break
                QTest.qWait(20)
        return popen.call_args[0][0][-1]

    def test_says_what_it_did(self):
        text = self.unstick({"Keyboard Craft Keyboard": [29, 14]}, [False])
        self.assertIn("Keyboard Craft Keyboard still held Ctrl, Backspace: released too", text)
        self.assertNotIn(("tap", 97), self.keys.sent)                   # (no grab: no Right Ctrl)
        self.assertEqual(self.unstick({}, [False]), "Shift, Ctrl, Alt and Super were pressed and let go.")
        log = (self.tmp / "unstick.log").read_text()
        self.assertIn("held keys released: Keyboard Craft Keyboard: Ctrl, Backspace; desktop mode's input grab: off", log)
        self.assertIn("held keys released: nothing", log)

    def test_gives_back_a_grab_and_checks(self):
        """Desktop mode's input grab (title "...to ungrab input"): one Right Ctrl tap, then the title
        says whether it let go."""
        text = self.unstick({}, [True, False])
        self.assertEqual(self.keys.sent.count(("tap", 97)), 1)
        self.assertIn("Desktop mode had taken all input, so other windows didn't get it: given back.", text)
        text = self.unstick({}, [True, True])
        self.assertEqual(self.keys.sent.count(("tap", 97)), 2)
        self.assertIn("didn't give it back: tap Right Ctrl on a keyboard", text)
        self.assertIn("still on after Right Ctrl", (self.tmp / "unstick.log").read_text())


class Mic(PadTest):
    def test_without_dictation_it_says_so(self):
        """🎤 with Dictation not installed: a dialog offering to open Frame Tweaks on it (lib/needs.py;
        starting the missing program raised, and an error inside a button's handler aborts the pad)."""
        home, started = self.tmp / "home", []
        self.pad.layer = "tools"
        with mock.patch.object(self.ap.Path, "home", return_value=home), \
                mock.patch.object(self.ap.subprocess, "Popen", lambda cmd, **kw: started.append(cmd)), \
                mock.patch.object(self.ap.needs, "offer") as offer:
            self.tap("🎤")
            self.assertEqual(offer.call_args.args[0], "dictation")
            self.assertEqual(started, [])
            (home / ".local/bin").mkdir(parents=True)
            (home / ".local/bin/dictate").touch()
            self.tap("🎤")
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


class Wander(PadTest):
    """A laser's jitter at a key's edge slides it off the key and back while the trigger is held:
    Qt says "released" each time it slides off and "pressed" each time it's back, and the pad acted
    on each. One Paste sent Ctrl+V three times, 🎤 started, stopped and restarted dictation, Snip
    opened three times, and a wavering tap on Ctrl left it locked. (A mouse on the desktop pad the
    same; the VR panel's laser input: WanderInVR.)"""

    def setUp(self):
        super().setUp()
        self.started = []
        home = self.tmp / "home"
        (home / ".local/bin").mkdir(parents=True)
        for tool in ("dictate", "frame-snip"):
            (home / ".local/bin" / tool).touch()
        for p in (mock.patch.object(self.ap.Path, "home", return_value=home),
                  mock.patch.object(self.ap.subprocess, "Popen", lambda cmd, **kw: self.started.append(Path(cmd[0]).name))):
            p.start()
            self.addCleanup(p.stop)

    def test_a_button_acts_once(self):
        self.tap("Paste", wander=2)
        self.assertEqual(self.keys.sent, [("tap", 29, 47)])
        self.tap("🎤", layer="tools", wander=2)
        self.tap("Snip", wander=2)
        self.assertEqual(self.started, ["dictate", "frame-snip"])
        self.tap("Tools", wander=1)
        self.assertEqual(self.pad.layer, "nav")                         # (back once; twice was tools again)

    def test_let_go_off_the_button_it_does_nothing(self):
        self.tap("Paste", let_go_on=False)
        self.tap("🎤", layer="tools", wander=1, let_go_on=False)
        self.assertEqual((self.keys.sent, self.started), ([], []))

    def test_a_wavering_tap_on_a_modifier_is_a_tap(self):
        self.tap("Ctrl", wander=2)
        self.assertEqual(self.pad.mod_state["Ctrl"], "oneshot")         # (it was locked)
        self.assertEqual(self.keys.sent, [(29, True)])                  # down, for the next key
        self.tap("Super", wander=1)
        self.tap("Super", wander=1)
        self.assertEqual(self.pad.mod_state["Super"], "locked")         # a double tap is still one

    def test_a_modifier_let_go_off_the_key_lets_go(self):
        self.tap("Alt", wander=1, let_go_on=False)
        self.assertEqual(self.pad.mod_state["Alt"], "off")              # (not one-shot: no tap)
        self.assertEqual(self.keys.sent, [(56, True), (56, False)])

    def test_a_held_key_is_down_while_the_pointer_holds_it(self):
        """↓, Bksp…: down while pressed, as Qt draws the key."""
        self.tap("↓", wander=1)
        self.assertEqual(self.keys.sent, [(108, True), (108, False), (108, True), (108, False)])
        self.keys.sent.clear()
        b = self.at("↓")[2]
        self.mouse(b, "press")
        self.mouse(b, "release", on=False)          # (let go off it with no move before: Qt said nothing)
        self.assertEqual(self.keys.sent, [(108, True), (108, False)])


def overlay_host(test):
    """The VR panel (vroverlay.py's OverlayHost) on the test's pad, with a stand-in openvr whose
    laser events a test scripts (laser())."""
    ov = types.ModuleType("openvr")
    ov.VREvent_MouseMove, ov.VREvent_MouseButtonDown, ov.VREvent_MouseButtonUp = 300, 301, 302
    ov.VREvent_FocusLeave, ov.k_unTrackedDeviceIndexInvalid = 304, 2 ** 32 - 1

    class Ev:
        def __init__(self):
            self.eventType, self.trackedDeviceIndex = 0, 1
            self.data = types.SimpleNamespace(mouse=types.SimpleNamespace(x=0.0, y=0.0, cursorIndex=0))
    ov.VREvent_t = Ev
    with mock.patch.dict(sys.modules, {"openvr": ov}):
        v = module("vroverlay", PAD / "vroverlay.py")
    test.pad.show()
    test.addCleanup(test.pad.hide)
    test.app.processEvents()
    o = v.OverlayHost.__new__(v.OverlayHost)
    o.pad, o.pressed, o.drag, o.gripping, o.hovered_devices, o.laser_at = test.pad, {}, None, set(), set(), {}
    o.hover, o.front, o.handles, o.input_handle = None, 0, [1], 1
    o.input_size = (test.pad.width(), test.pad.height())
    o.log_input = lambda msg: None                                       # (not /run/user's log)
    o.poll_error = 0.0
    return o


class WanderInVR(PadTest):
    """The same through the VR panel's own input path (vroverlay.py pump) from a stand-in openvr:
    one trigger pull, its laser wavering across the key's edge."""
    MOVE, DOWN, UP = 300, 301, 302

    def setUp(self):
        super().setUp()
        self.o = overlay_host(self)

    def laser(self, *steps):
        """steps: (event, key, on the key or just off its edge), laser 0's, each on its own."""
        for kind, name, on in steps:
            b = self.at(name)[2]
            p = b.mapTo(self.pad, b.rect().center())
            queue = [(kind, p.x() + (0 if on else b.width() // 2 + 2), self.o.input_size[1] - p.y())]

            def poll(handle, ev, queue=queue):
                if not queue:
                    return (False, ev)
                ev.eventType, ev.data.mouse.x, ev.data.mouse.y = queue.pop(0)
                return (True, ev)
            self.o.ov = types.SimpleNamespace(pollNextOverlayEvent=poll)
            self.o.last_button_time = {}            # (each its own event, not one seen twice)
            self.o.pump(1)

    def test_one_trigger_pull_acts_once(self):
        M, D, U = self.MOVE, self.DOWN, self.UP
        self.laser((M, "Paste", True), (D, "Paste", True), (M, "Paste", False), (M, "Paste", True),
                   (M, "Paste", False), (M, "Paste", True), (U, "Paste", True))
        self.assertEqual(self.keys.sent, [("tap", 29, 47)])
        self.laser((D, "Ctrl", True), (M, "Ctrl", False), (M, "Ctrl", True), (U, "Ctrl", True))
        self.assertEqual(self.pad.mod_state["Ctrl"], "oneshot")

    def test_a_lost_release_doesnt_keep_a_modifier_down(self):
        """The laser that held Ctrl presses ← without its release ever arriving: that press was
        over, so Ctrl goes up first (it would have stayed down, ← a Ctrl+←)."""
        M, D, U = self.MOVE, self.DOWN, self.UP
        self.laser((D, "Ctrl", True), (M, "←", True), (D, "←", True), (U, "←", True))
        self.assertEqual(self.keys.sent, [(29, True), (29, False), (105, True), (105, False)])
        self.assertEqual(self.pad.mod_state["Ctrl"], "off")
        self.assertEqual(self.pad.held, {})


@unittest.skipUnless(layouts_compile(), "needs libxkbcommon and XKB's layouts")
class Layouts(PadTest):
    """Shortcut letters where the desktop's keyboard layout has them (lib/xkb.py): the US keys'
    codes were sent, so on a French keyboard Select all was Ctrl+Q (Quit) and Undo Ctrl+W (close
    the tab), and on a German or Swiss one Undo and Redo were Ctrl+Y."""
    ORDER = (("nav", "All"), ("nav", "Undo"), ("nav", "Copy"), ("nav", "Paste"), ("nav", "Cut"),
             ("tools", "Redo"), ("tools", "Find"), ("tools", "Save"))
    US = [(30,), (44,), (46,), (47,), (45,), (42, 44), (33,), (31,)]

    def shortcuts(self, kxkbrc):
        (self.tmp / "config").mkdir(exist_ok=True)
        (self.tmp / "config/kxkbrc").write_text(kxkbrc)
        if getattr(self.ap, "xkb", None):
            self.ap.xkb._current.update(at=None)                       # (looked at again now)
        self.keys.sent.clear()
        for layer, name in self.ORDER:
            self.tap(name, layer=layer)
        self.assertTrue(all(s[:2] == ("tap", 29) for s in self.keys.sent))
        return [s[2:] for s in self.keys.sent]

    def test_each_layout(self):
        for layout, keys in (("us", self.US),
                             ("fr", [(16,), (17,), (46,), (47,), (45,), (42, 17), (33,), (31,)]),
                             ("de\nVariantList=nodeadkeys", [(30,), (21,), (46,), (47,), (45,), (42, 21), (33,), (31,)]),
                             ("ch", [(30,), (21,), (46,), (47,), (45,), (42, 21), (33,), (31,)]),
                             ("latam", self.US),
                             ("ru", self.US)):            # (no Latin letters: programs match the US keys)
            with self.subTest(layout):
                self.assertEqual(self.shortcuts(f"[Layout]\nLayoutList={layout}\nUse=true\n"), keys)

    def test_the_us_keys_without_libxkbcommon(self):
        x = getattr(self.ap, "xkb", None)
        with mock.patch.dict(x._lib if x else {}, {"lib": None}), mock.patch.dict(x._keymaps if x else {}, clear=True):
            self.assertEqual(self.shortcuts("[Layout]\nLayoutList=fr\n"), self.US)


class GoingAway(PadTest):
    """A pad that goes away lets go of what it holds down: ydotoold's virtual keyboard is the whole
    Frame's, and a Ctrl it left down made every click a Ctrl+click until something let go of it."""

    def setUp(self):
        super().setUp()
        self.ydotoold, yd = ydotoold(self)
        self.pad = self.ap.ArrowPad(yd, None)
        self.handlers = {}
        p = mock.patch.object(signal, "signal", side_effect=self.handlers.__setitem__)      # (not this process's)
        p.start()
        self.addCleanup(p.stop)
        from PyQt6.QtCore import qInstallMessageHandler
        self.addCleanup(qInstallMessageHandler, None)                   # (Qt's own again)

    def test_desktop_mode_ending(self):
        """Desktop mode's display goes away: Qt says "The X11 connection broke" and ends the program
        there and then, without closing the pad. Its message handler lets go first."""
        from PyQt6.QtCore import qWarning
        self.tap("Ctrl")                                    # one-shot: down until the next key
        self.mouse(self.at("↓")[2], "press")                # and ↓ held
        self.assertEqual(received(self.ydotoold), [(29, 1), (108, 1)])
        self.ap.let_go_on_exit(self.pad)
        with mock.patch.object(sys, "stderr", io.StringIO()) as err:
            qWarning("The X11 connection broke (error 1). Did the X11 server die?")
        self.assertEqual(sorted(received(self.ydotoold)), [(29, 0), (108, 0)])
        self.assertIn("The X11 connection broke", err.getvalue())       # (still printed, as Qt does)

    def test_an_error_qt_aborts_on(self):
        """An error PyQt6 doesn't catch (a SteamVR call failing in the VR panel, say) aborts the
        pad through a fatal message: its handler lets go first, as for the X11 connection."""
        from PyQt6.QtCore import QtMsgType
        self.tap("Ctrl")
        self.tap("Alt")
        self.tap("Alt")                                     # locked
        received(self.ydotoold)
        handlers = []
        with mock.patch.object(self.ap, "qInstallMessageHandler", handlers.append):
            self.ap.let_go_on_exit(self.pad)
        with mock.patch.object(sys, "stderr", io.StringIO()):
            handlers[0](QtMsgType.QtFatalMsg, None, "Unhandled Python exception")
        self.assertEqual(sorted(received(self.ydotoold)), [(29, 0), (56, 0)])

    def test_a_stop(self):
        """SIGTERM (an update or an uninstall stopping it): it lets go, then closes as ✕ does."""
        from PyQt6.QtTest import QTest
        self.tap("Super")
        self.tap("Super")                                   # locked
        self.ap.let_go_on_exit(self.pad)
        with mock.patch.object(self.pad, "close") as close:
            self.handlers[signal.SIGTERM](signal.SIGTERM, None)
            self.assertEqual(received(self.ydotoold), [(125, 1), (125, 0)])
            for _ in range(250):                # (closed from the event loop: later on a busy machine)
                if close.called:
                    break
                QTest.qWait(20)
        close.assert_called_once_with()

    def test_the_dashboard_closing(self):
        """VR: when the dashboard closes, the panel lets go of everything before it asks SteamVR to
        hide (a SteamVR call that failed ended the pad, and the keys stayed down). A call that
        fails is let go now: the pad goes on, and the next tick tries again."""
        from PyQt6.QtCore import QEvent, Qt
        o = overlay_host(self)
        self.tap("Ctrl")
        self.tap("Ctrl")                                    # locked
        b = self.at("↓")[2]
        o.send(b, QEvent.Type.MouseButtonPress, b.mapTo(self.pad, b.rect().center()), Qt.MouseButton.LeftButton)
        o.pressed[0] = b                                    # held by laser 0
        received(self.ydotoold)

        def gone(handle):
            raise RuntimeError("SteamVR went away")
        o.ov = types.SimpleNamespace(isDashboardVisible=lambda: False, hideOverlay=gone)
        o.ticks, o._dash, o.visible, o.cover, o.input_handle = 0, True, True, None, 7
        o.grips, o.dirty = None, False
        with mock.patch.object(sys, "stderr", io.StringIO()) as err:
            o.poll()
        self.assertIn("SteamVR went away", err.getvalue())
        self.assertEqual(sorted(received(self.ydotoold)), [(29, 0), (108, 0)])

    def test_placed_without_a_headset_pose(self):
        """Reset (or a start) with neither a dashboard bar to follow nor a headset pose (SteamVR
        starting again): it crashed on None. Now: where it is, or in front of where you'd stand."""
        o = overlay_host(self)
        o.reset_position.__globals__["openvr"].k_unTrackedDeviceIndex_Hmd = 0      # (the stand-in's)
        o.device_matrix = lambda index: None
        o.dashboard_anchor = lambda keys=None: None
        o.width_m = 0.5
        o.apply_pose = o.remember_offset = o.save = lambda: None
        o.pose = None
        o.reset_position()
        self.assertAlmostEqual(o.pose[1][3], 1.6 - 0.5, delta=0.6)             # (about head height, a bit under)
        before = [row[:] for row in o.pose]
        o.reset_position()
        self.assertEqual(o.pose, before)


class DesktopGrabbed(PadTest):
    """Unstick gives desktop mode's input grab back (Right Ctrl) only when the desktop's window says
    the grab is on. KWin says it in desktop mode's language (SteamOS ships its catalogues), so on a
    German, French or Spanish desktop the English title was never found, and the grab never given
    back. (Here: catalogues with KWin 6.2's own translations.)"""
    CATALOGUES = {
        "de": {"KDE Wayland Compositor": "KDE-Wayland-Compositor"},      # (the hints aren't translated)
        "fr": {"KDE Wayland Compositor": "Compositeur Wayland de KDE",
               "Press right control key to grab input": "Appuyez sur la touche de contrôle droite pour saisir l'entrée",
               "Press right control to ungrab input": "Appuyez sur la touche de contrôle droit pour libérer la saisie"},
        "es": {"KDE Wayland Compositor": "Compositor de KDE Wayland",
               "Press right control key to grab input": "Pulse la tecla de Control derecha para capturar la entrada",
               "Press right control to ungrab input": "Pulse la tecla de Control derecha para liberar la entrada"},
    }

    def setUp(self):
        super().setUp()
        for lang, messages in self.CATALOGUES.items():
            (self.tmp / "locale" / lang / "LC_MESSAGES").mkdir(parents=True)
            (self.tmp / "locale" / lang / "LC_MESSAGES/kwin.mo").write_bytes(mo(messages))
        (self.tmp / "stubs").mkdir()
        for p in (mock.patch.object(self.ap, "KWIN_LOCALE", self.tmp / "locale", create=True),
                  mock.patch.dict(os.environ, {"PATH": f"{self.tmp / 'stubs'}:{os.environ['PATH']}"})):
            p.start()
            self.addCleanup(p.stop)

    def grabbed(self, language, *titles):
        """desktop_grabbed(), desktop mode speaking `language`, these window titles on :0 (as
        xwininfo prints them: bytes)."""
        lines = b"\n".join(b'     0x%x "%s": ()  1920x1080+0+0  +0+0' % (0x3e00000 + i, t) for i, t in enumerate(titles))
        stub = self.tmp / "stubs/xwininfo"
        stub.write_bytes(b"#!/bin/sh\ncat <<'EOF'\n\nxwininfo: Window id: 0x26f (the root window) (has no name)\n\n"
                         + lines + b"\nEOF\n")
        stub.chmod(0o755)
        with mock.patch.object(self.ap, "desktop_languages", return_value=[language], create=True):
            return self.ap.desktop_grabbed()

    def test_in_each_language(self):
        english = ("Press right control to ungrab input", "Press right control key to grab input")
        for lang in ("en", "de", "fr", "es"):
            t = {"en": {}, **self.CATALOGUES}[lang]
            name = t.get("KDE Wayland Compositor", "KDE Wayland Compositor")
            ungrab, grab = (t.get(h, h) for h in english)
            with self.subTest(lang):
                self.assertTrue(self.grabbed(lang, f"{name} - {ungrab}".encode()))
                self.assertFalse(self.grabbed(lang, f"{name} - {grab}".encode()))

    def test_only_when_the_desktops_window_says_so(self):
        """(A browser tab about it isn't desktop mode, nor is a title in a language it isn't in.)"""
        self.assertFalse(self.grabbed("en", b"Firefox - Press right control to ungrab input"))
        fr = self.CATALOGUES["fr"]
        self.assertFalse(self.grabbed("es", f"{fr['KDE Wayland Compositor']} - {fr['Press right control to ungrab input']}".encode()))
        self.assertFalse(self.grabbed("en", b"KDE Wayland Compositor"))

    def test_a_title_that_isnt_utf8(self):
        """Another window's Latin-1 title (no _NET_WM_NAME) can't be read as UTF-8: Unstick crashed
        the pad."""
        self.assertTrue(self.grabbed("en", b"Caf\xe9 au lait", b"KDE Wayland Compositor - Press right control to ungrab input"))
        self.assertFalse(self.grabbed("en", b"Caf\xe9", b"KDE Wayland Compositor - Press right control key to grab input"))

    def test_desktop_modes_languages(self):
        """As KDE picks them, from desktop mode's own environment; without it, this program's."""
        with mock.patch.object(self.ap, "desktop_env", return_value={"LANGUAGE": "fr:de", "LANG": "fr_FR.UTF-8"}):
            self.assertEqual(self.ap.desktop_languages(), ["fr", "de", "fr_FR.UTF-8"])
        with mock.patch.object(self.ap, "desktop_env", return_value=None), \
                mock.patch.dict(os.environ, {"LANGUAGE": "es_419", "LC_ALL": "C", "LANG": "C.UTF-8"}):
            self.assertEqual(self.ap.desktop_languages()[0], "es_419")


if __name__ == "__main__":
    unittest.main()
