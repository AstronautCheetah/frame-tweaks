"""adb-scrcpy/phone-touch: laser positions on the mirror become scrcpy touch messages."""
import sys
import re
import struct
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
pt = load_script(ROOT / "packs/core/adb-scrcpy" / "phone-touch", "phone_touch")


def phone(size=(1080, 2400)):
    with mock.patch.object(pt, "scrcpy_server", return_value=("5.0.1", "/x")):
        p = pt.Phone("10.0.0.2:5555")
    p.size, p.sock = size, mock.Mock()
    return p


def sent(p):
    return struct.unpack(">BBqiiHHHII", p.sock.sendall.call_args[0][0])


class Touch(unittest.TestCase):
    def test_message_is_scrcpys_32_byte_touch(self):
        p = phone()
        p.touch(pt.DOWN, 0.5, 0.25, sideways=False)
        self.assertEqual(len(p.sock.sendall.call_args[0][0]), 32)
        self.assertEqual(sent(p), (2, 0, -2, 540, 600, 1080, 2400, 0xFFFF, 0, 0))

    def test_a_press_wakes_the_phone_first(self):
        """A phone asleep ignores touches: each press sends Android's WAKEUP key (down, up) first;
        a move or a lift doesn't."""
        p = phone()
        p.touch(pt.DOWN, 0.5, 0.25, sideways=False)
        msgs = [c[0][0] for c in p.sock.sendall.call_args_list]
        self.assertEqual([struct.unpack(">BBIII", m) for m in msgs[:2]], [(0, 0, 224, 0, 0), (0, 1, 224, 0, 0)])
        self.assertEqual(struct.unpack(">BBqiiHHHII", msgs[2])[:2], (2, pt.DOWN))
        p.sock.reset_mock()
        p.touch(pt.MOVE, 0.5, 0.3, sideways=False)
        p.touch(pt.UP, 0.5, 0.3, sideways=False)
        self.assertEqual(len(p.sock.sendall.call_args_list), 2)

    def test_sideways_swaps_the_screen(self):
        p = phone()
        p.touch(pt.MOVE, 1.0, 1.0, sideways=True)
        self.assertEqual(sent(p)[3:7], (2399, 1079, 2400, 1080))

    def test_up_has_no_pressure_and_outside_is_clamped(self):
        p = phone()
        p.touch(pt.UP, -0.2, 1.4, sideways=False)
        t, action, _, x, y, _, _, pressure, _, _ = sent(p)
        self.assertEqual((action, x, y, pressure), (pt.UP, 0, 2399, 0))

    def test_scroll_is_scrcpys_21_byte_wheel(self):
        p = phone()
        p.scroll(0.5, 0.5, False, 0, 1)                 # a notch down
        msg = p.sock.sendall.call_args[0][0]
        self.assertEqual(len(msg), 21)
        self.assertEqual(struct.unpack(">BiiHHhhI", msg), (3, 540, 1200, 1080, 2400, 0, -2048, 0))

    def test_scroll_is_capped_at_16_notches(self):
        p = phone()
        p.scroll(0, 0, False, 40, -40)
        self.assertEqual(struct.unpack(">BiiHHhhI", p.sock.sendall.call_args[0][0])[5:7], (0x7FFF, 0x7FFF))

    def test_screen_size_takes_the_override(self):
        out = mock.Mock(stdout="Physical size: 1344x2992\nOverride size: 1080x2400\n")
        with mock.patch.object(pt, "adb", return_value=out):
            self.assertEqual(pt.screen_size("d"), (1080, 2400))


class PhoneNotAnswering(unittest.TestCase):
    """A phone that stops answering (a Wi-Fi link gone quiet) is tried again at the next touch;
    it used to end phone-touch, taking the layer and the joystick with it."""
    def test_adb_timing_out_is_an_oserror(self):
        with mock.patch.object(pt.subprocess, "run", side_effect=pt.subprocess.TimeoutExpired("adb", 20)):
            self.assertRaises(OSError, pt.adb, "d", "shell", "wm", "size")

    def test_touch_and_scroll_without_an_answer_are_dropped(self):
        p = phone()
        p.sock = None
        with mock.patch.object(pt.subprocess, "run", side_effect=pt.subprocess.TimeoutExpired("adb", 20)), \
                mock.patch.object(pt, "log"):
            p.touch(pt.DOWN, 0.5, 0.5, sideways=False)
            p.scroll(0.5, 0.5, False, 0, 1)
        self.assertIsNone(p.sock)

    def test_first_touch_connects_when_the_first_connection_failed(self):
        """(Before it learnt the screen size: the touch failed on the missing size.)"""
        with mock.patch.object(pt, "scrcpy_server", return_value=("5.0.1", "/x")):
            p = pt.Phone("10.0.0.2:5555")

        def connect():
            p.size, p.sock = (1080, 2400), mock.Mock()
        with mock.patch.object(p, "connect", side_effect=connect):
            p.touch(pt.DOWN, 0.5, 0.25, sideways=False)
        self.assertEqual(sent(p), (2, 0, -2, 540, 600, 1080, 2400, 0xFFFF, 0, 0))


DUMPSYS = """WINDOW MANAGER WINDOWS (dumpsys window windows)
  Window #0 Window{a1b2c3 u0 com.android.systemui/StatusBar}:
    mDisplayId=0 rootTaskId=1 mSession=Session{1 2:3}
    mAttrs={(0,0)(fillxfill) ty=STATUS_BAR fmt=TRANSLUCENT
      fl=NOT_FOCUSABLE SPLIT_TOUCH HARDWARE_ACCELERATED}
  Window #1 Window{d4e5f6 u0 com.bank.app/com.bank.app.Main}:
    mDisplayId=0 rootTaskId=12
    mAttrs={(0,0)(fillxfill) ty=BASE_APPLICATION wanim=0x1030465
      fl=LAYOUT_IN_SCREEN LAYOUT_INSET_DECOR SECURE SPLIT_TOUCH HARDWARE_ACCELERATED}
  Window #2 Window{778899 u0 com.example.notes/com.example.notes.Edit}:
    mAttrs={(0,0)(fillxfill) ty=BASE_APPLICATION
      fl=LAYOUT_IN_SCREEN SPLIT_TOUCH}

  mCurrentFocus=Window{FOCUS u0 X}
"""


class SecureScreen(unittest.TestCase):
    """An app hiding its screen from mirroring (FLAG_SECURE) shows black: phone-touch tells it from
    Android's window list, by the focused window's flags."""

    def test_the_focused_windows_flags_decide(self):
        bank = DUMPSYS.replace("Window{FOCUS u0 X}", "Window{d4e5f6 u0 com.bank.app/com.bank.app.Main}")
        notes = DUMPSYS.replace("Window{FOCUS u0 X}", "Window{778899 u0 com.example.notes/com.example.notes.Edit}")
        self.assertTrue(pt.focused_is_secure(bank))
        self.assertFalse(pt.focused_is_secure(notes))            # (SECURE on another window doesn't count)
        self.assertFalse(pt.focused_is_secure(DUMPSYS.replace("mCurrentFocus=Window{FOCUS u0 X}", "mCurrentFocus=null")))
        self.assertFalse(pt.focused_is_secure(""))
        # (A Pixel: two displays, the first with no focus; its PIN prompt focused on the second. Its
        # `dumpsys window windows` has no focus lines at all: watch_secure adds them from the full
        # dump, checked on the phone, not here.)
        two = DUMPSYS.replace("  mCurrentFocus=Window{FOCUS u0 X}\n",
                              "  mCurrentFocus=null\n  mCurrentFocus=Window{d4e5f6 u0 com.bank.app/com.bank.app.Main}\n")
        self.assertTrue(pt.focused_is_secure(two))

    def test_a_fingerprint_or_face_prompt_is_told_apart(self):
        """The phone's biometric prompt wants the sensor, not a PIN: its own notice (a Pixel's
        BiometricPrompt window, focused on its second display)."""
        bio = DUMPSYS.replace("Window{d4e5f6 u0 com.bank.app/com.bank.app.Main}", "Window{2304332 u0 BiometricPrompt}") \
                     .replace("  mCurrentFocus=Window{FOCUS u0 X}\n",
                              "  mCurrentFocus=null\n  mCurrentFocus=Window{2304332 u0 BiometricPrompt}\n")
        self.assertEqual(pt.hidden_kind(bio), "biometric")
        bank = DUMPSYS.replace("Window{FOCUS u0 X}", "Window{d4e5f6 u0 com.bank.app/com.bank.app.Main}")
        self.assertEqual(pt.hidden_kind(bank), "screen")
        self.assertEqual(pt.hidden_kind(DUMPSYS), "")
        js = (ROOT / "packs/core/adb-scrcpy" / "phone-touch.js").read_text()
        self.assertIn("window.__sftPhoneSecure === 'biometric'", js)

    def test_the_fingerprint_sensor_spot(self):
        """The fingerprint goes where the sensor is: its overlay window's frame while the prompt shows
        it, else a Pixel's usual spot."""
        udfps = DUMPSYS.replace("Window #2 Window{778899 u0 com.example.notes/com.example.notes.Edit}:",
                                "Window #2 Window{a1ee52e u0 UdfpsControllerOverlay}:\n"
                                "    Frames: parent=[0,0][1344,2992] display=[0,0][1344,2992] frame=[522,2400][822,2700]")
        spot = pt.sensor_spot(udfps, (1344, 2992))
        self.assertAlmostEqual(spot["u"], 672 / 1344)
        self.assertAlmostEqual(spot["v"], 2550 / 2992)
        self.assertAlmostEqual(spot["d"], 300 / 1344)
        self.assertEqual(pt.sensor_spot(DUMPSYS, (1344, 2992)), pt.SENSOR_GUESS)
        self.assertEqual(pt.sensor_spot(udfps, None), pt.SENSOR_GUESS)          # (screen size not known yet)

    def test_checked_every_second_while_hidden(self):
        """The notice and keypads stayed up several seconds after unlocking: while the screen is
        hidden it's checked every second (3 s otherwise)."""
        hidden = DUMPSYS.replace("Window{FOCUS u0 X}", "Window{d4e5f6 u0 com.bank.app/com.bank.app.Main}")
        answers = iter([hidden, hidden, DUMPSYS, DUMPSYS])
        sleeps, state = [], {}
        runs = iter([True, True, True, True, False])
        with mock.patch.object(pt, "scrcpy_running", lambda: next(runs)), \
                mock.patch.object(pt, "adb", lambda *a: mock.Mock(returncode=0, stdout=next(answers))), \
                mock.patch.object(pt.time, "sleep", sleeps.append):
            pt.watch_secure("d", state)
        self.assertEqual(sleeps, [1.0, 1.0, 3.0, 3.0])

    def test_the_layer_shows_a_notice_while_it_is_hidden(self):
        js = (ROOT / "packs/core/adb-scrcpy" / "phone-touch.js").read_text()
        layer = js.split("const buildLayer", 1)[1].split("// ---- the gear", 1)[0]
        self.assertIn("window.__sftPhoneSecure", layer)              # (the notice: in the picture)
        self.assertIn("...over", layer)
        # The keypad's digits take no clicks (taps reach the phone through them); its controls
        # (the keypad button, the nudge arrows) never reach the phone as touches.
        pad = layer.split("key: 'pad'", 1)[1].split("// The arrows", 1)[0]
        self.assertIn("pointerEvents: 'none'", pad)
        self.assertIn("ev.stopPropagation(); ev.preventDefault()", layer)
        self.assertEqual(layer.count("['↖', -1, -1]"), 1)
        self.assertEqual(len(re.findall(r"\['[↖↑↗←→↙↓↘]', -?[01], -?[01]\]", layer)), 8)
        src = (ROOT / "packs/core/adb-scrcpy" / "phone-touch").read_text()
        self.assertIn("window.__sftPhoneSecure = ", src)


class UnlockKeypad(unittest.TestCase):
    """The unlock keypad types on the phone as a keyboard would: digits, Delete, Enter only; its
    digits are never logged or counted where a trail could show them."""

    def test_keys_are_androids_and_only_these(self):
        self.assertEqual(pt.UNLOCK_KEYS["0"], 7)
        self.assertEqual(pt.UNLOCK_KEYS["9"], 16)
        self.assertEqual((pt.UNLOCK_KEYS["del"], pt.UNLOCK_KEYS["enter"]), (67, 66))
        self.assertEqual(set(pt.UNLOCK_KEYS), {*"0123456789", "del", "enter"})

    def test_a_key_is_pressed_and_let_go(self):
        p = phone()
        p.key(pt.UNLOCK_KEYS["5"])
        msgs = [struct.unpack(">BBIII", c[0][0]) for c in p.sock.sendall.call_args_list]
        self.assertEqual(msgs, [(0, 0, 12, 0, 0), (0, 1, 12, 0, 0)])

    def test_show_pin_wakes_then_swipes_up(self):
        p = phone()
        with mock.patch.object(pt.time, "sleep"):
            p.show_pin()
        msgs = [c[0][0] for c in p.sock.sendall.call_args_list]
        self.assertEqual(struct.unpack(">BBIII", msgs[0])[2], pt.KEYCODE_WAKEUP)
        touches = [struct.unpack(">BBqiiHHHII", m) for m in msgs if len(m) == 32]
        downs = [t for t in touches if t[1] == pt.DOWN]
        self.assertEqual(len(downs), 1)
        self.assertGreater(downs[0][4], touches[-1][4])               # (from low on the screen, up)
        self.assertEqual(touches[-1][1], pt.UP)

    def test_hardware_key_buttons(self):
        """The buttons below the mirror press Android's Back, App switcher and volume keys; each has a
        setting of its own, off unless turned on, in the gear's panel and the window's ⚙ Settings."""
        self.assertEqual(pt.HW_KEYS, {"back": 4, "recents": 187, "vol_up": 24, "vol_down": 25})
        for key in ("PHONE_KEY_BACK", "PHONE_KEY_RECENTS", "PHONE_KEY_VOLUP", "PHONE_KEY_VOLDOWN"):
            self.assertEqual((pt.CHOICES[key], pt.DEFAULTS[key]), (("on", "off"), "off"))
        js = (ROOT / "packs/core/adb-scrcpy" / "phone-touch.js").read_text()
        self.assertIn("call({ a: 'hwkey', k: k2 })", js)
        for name in pt.HW_KEYS:
            self.assertIn(f"'{name}'", js)

    def test_the_layer_never_records_a_digit(self):
        js = (ROOT / "packs/core/adb-scrcpy" / "phone-touch.js").read_text()
        pad = js.split("const typingPad", 1)[1].split("const hidden", 1)[0]
        self.assertIn("call({ a: 'key', k })", pad)
        self.assertNotIn("mark(", pad)
        self.assertNotIn("stats", pad)
        src = (ROOT / "packs/core/adb-scrcpy" / "phone-touch").read_text()
        handler = src.split('if req["a"] == "key":', 1)[1].split("continue", 1)[0]
        self.assertNotIn("log(", handler)


class Replaced(unittest.TestCase):
    def test_the_one_replaced_cleans_up(self):
        """A reconnect's phone-touch stops the one before (SIGTERM): that one removes its tunnel
        and stops its server first, as when scrcpy closes (it ended on the spot)."""
        import signal
        import tempfile
        handlers, the_phone = {}, mock.Mock()

        def serve(*a):
            handlers[signal.SIGTERM](signal.SIGTERM, None)      # the next one's SIGTERM arrives
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "sft-dashboard").touch()
            with mock.patch.object(pt.sys, "argv", ["phone-touch", "10.0.0.2:5555"]), \
                    mock.patch.object(pt, "DASHBOARD", Path(d) / "sft-dashboard"), \
                    mock.patch.object(pt, "PIDFILE", Path(d) / "pid"), \
                    mock.patch.object(pt.signal, "signal", side_effect=handlers.__setitem__), \
                    mock.patch.object(pt, "Phone", return_value=the_phone), \
                    mock.patch.object(pt, "scrcpy_running", return_value=True), \
                    mock.patch.object(pt.threading, "Thread"), mock.patch.object(pt, "dashboard"), \
                    mock.patch.object(pt, "serve", side_effect=serve):
                self.assertRaises(SystemExit, pt.main)
            self.assertFalse((Path(d) / "pid").exists())
        the_phone.close.assert_called_once()


class Stop(BaseException):
    """Ends serve()'s endless loop in a test (time.sleep raises it)."""


class BindingAfterAReload(unittest.TestCase):
    def test_runtime_is_on_before_the_binding(self):
        """As sft-dashboard's: a reloaded dashboard page gets the binding again only while the
        Runtime domain is on (Runtime.enable before Runtime.addBinding)."""
        import types
        sent = []

        class Page:                                          # the dashboard page's DevTools connection
            rest = b"..."                                    # (a message waiting: no select())

            def __init__(self, url, timeout=None):
                pass

            def send(self, obj):
                sent.append(obj["method"])

            def recv(self):
                raise OSError("closed")                      # (then: wait and connect again)
        sd = types.SimpleNamespace(systemui=lambda: "ws://127.0.0.1:1/devtools/page/1", Ws=Page)
        with mock.patch.object(pt, "scrcpy_running", return_value=True), mock.patch.object(pt, "publish"), \
                mock.patch.object(pt, "log"), mock.patch.object(pt.time, "sleep", side_effect=Stop):
            with self.assertRaises(Stop):
                pt.serve(mock.Mock(), sd, {})
        self.assertEqual(sent[:2], ["Runtime.enable", "Runtime.addBinding"])


class Joystick(unittest.TestCase):
    def rot_x(self, deg):
        c, s = pt.math.cos(pt.math.radians(deg)), pt.math.sin(pt.math.radians(deg))
        return [[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0]]

    def test_rotation_vector_reads_the_tilt(self):
        rest = self.rot_x(0)
        x, y, z = pt.rotation_vector(self.rot_x(-20), rest)
        self.assertAlmostEqual(x, -20, places=3)
        self.assertEqual((round(y, 6), round(z, 6)), (0, 0))
        self.assertEqual(pt.rotation_vector(rest, rest), (0.0, 0.0, 0.0))

    def test_rate_has_a_dead_zone_and_keeps_the_sign(self):
        self.assertEqual(pt.stick_rate(0.15), 0.0)
        self.assertEqual(pt.stick_rate(-1.0), -15.0)
        self.assertLess(pt.stick_rate(0.5), pt.stick_rate(0.9))

    def test_scrcpy_is_looked_for_every_2_s_not_every_tick(self):
        """(A pgrep takes some 20 ms of processor time: 30 a second took a good part of a core.)"""
        import types
        clock = [1000.0]
        fake_time = types.SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
        looks = []

        def running():
            looks.append(clock[0])
            return clock[0] < 1010                          # the mirror closes after 10 s
        with mock.patch.object(pt, "time", fake_time), mock.patch.object(pt, "Sticks"), \
                mock.patch.object(pt, "scrcpy_running", side_effect=running):
            pt.scroll_with_sticks(phone(), {})
        self.assertLessEqual(len(looks), 7)                 # (it was every 1/30 s: 300 times)
        self.assertGreaterEqual(clock[0], 1010)             # and it still stops with the mirror


class Settings(unittest.TestCase):
    def test_write_keeps_other_lines_and_replaces_ours(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            conf = Path(d) / "phone.conf"
            conf.write_text('PHONE_NAME="My phone"\n# note\nPHONE_MAX_SIZE=1280\nPHONE_MAX_SIZE=800\n')
            pt.write_conf({"PHONE_MAX_SIZE": "1024", "PHONE_STICK_SPEED": "25", "EVIL": "x", "PHONE_MAX_FPS": "7"}, conf)
            self.assertEqual(conf.read_text(),
                             'PHONE_NAME="My phone"\n# note\nPHONE_MAX_SIZE=1024\nPHONE_STICK_SPEED=25\n')
            got = pt.read_conf(conf)
            self.assertEqual((got["PHONE_MAX_SIZE"], got["PHONE_STICK_SPEED"], got["PHONE_MAX_FPS"]), ("1024", "25", "60"))

    def test_read_ignores_unknown_values(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            conf = Path(d) / "phone.conf"
            conf.write_text("PHONE_BIT_RATE=$(rm -rf ~)\n")
            self.assertEqual(pt.read_conf(conf)["PHONE_BIT_RATE"], "2M")


class Defaults(unittest.TestCase):
    def test_panel_and_helper_agree(self):
        import re
        js = (ROOT / "packs/core/adb-scrcpy" / "phone-touch.js").read_text()
        found = dict(re.findall(r"(PHONE_\w+): '([^']+)'", re.search(r"const DEFAULTS = \{([^}]*)\}", js).group(1)))
        self.assertEqual(found, pt.DEFAULTS)
        for key, value in pt.DEFAULTS.items():
            self.assertIn(value, pt.CHOICES[key])
        self.assertIn('PHONE_MAX_SIZE:-1024', (ROOT / "packs/core/adb-scrcpy" / "phone").read_text())
        self.assertIn('PHONE_BIT_RATE:-2M', (ROOT / "packs/core/adb-scrcpy" / "phone").read_text())

    def test_reset_keeps_other_lines(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            conf = Path(d) / "phone.conf"
            conf.write_text('PHONE_NAME="x"\nPHONE_MAX_FPS=120\n')
            pt.reset_conf(conf)
            self.assertEqual(conf.read_text(), 'PHONE_NAME="x"\n')


class RestartStream(unittest.TestCase):
    def test_leaves_the_request_then_signals(self):
        """The request file first (phone looks for it: bash can lose the signal's trap), then
        SIGUSR1 to hurry it."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            request = Path(d) / "sft-phone.restart"
            seen = []
            with mock.patch.object(pt, "PHONE_RESTART", request), mock.patch.object(pt, "running", return_value=4321), \
                    mock.patch.object(pt.os, "kill", side_effect=lambda pid, sig: seen.append((pid, sig, request.exists()))):
                pt.restart_stream()
            self.assertEqual(seen, [(4321, 10, True)])


class UntestedScrcpy(unittest.TestCase):
    """With a scrcpy major version it wasn't tested with, phone-touch stays off (once-only notice)."""
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(pt, "STATE", Path(self.tmp.name)).start()
        self.run = mock.patch.object(pt.subprocess, "run").start()
        mock.patch.dict(pt.os.environ, {"PHONE_TOUCH_ANY_SCRCPY": ""}).start()

    def check(self, version):
        with mock.patch.object(pt, "scrcpy_server", return_value=(version, "/x")), mock.patch.object(pt, "log"):
            return pt.check()

    def test_tested_version_passes_silently(self):
        self.assertEqual(self.check("5.2"), 0)
        self.run.assert_not_called()

    def test_untested_version_is_refused_and_notified_once(self):
        self.assertEqual(self.check("6.0"), 1)
        self.assertEqual(self.check("6.0"), 1)
        self.assertEqual(self.run.call_count, 1)
        self.assertEqual(self.run.call_args[0][0][0], "notify-send")
        self.assertEqual(self.check("7.1"), 1)                  # a new version: told again
        self.assertEqual(self.run.call_count, 2)

    def test_override(self):
        pt.os.environ["PHONE_TOUCH_ANY_SCRCPY"] = "1"
        self.assertEqual(self.check("6.0"), 0)

    def test_tested_versions_file_agrees(self):
        line = next(l for l in (ROOT / "lib/tested-versions").read_text().splitlines() if l.startswith("scrcpy="))
        self.assertIn(line.split("=")[1].split(".")[0], pt.SCRCPY_TESTED)


if __name__ == "__main__":
    unittest.main()
