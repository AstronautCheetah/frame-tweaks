"""adb-scrcpy/phone-touch: laser positions on the mirror become scrcpy touch messages."""
import importlib.machinery
import importlib.util
import struct
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_l = importlib.machinery.SourceFileLoader("phone_touch", str(ROOT / "adb-scrcpy" / "phone-touch"))
pt = importlib.util.module_from_spec(importlib.util.spec_from_loader("phone_touch", _l))
_l.exec_module(pt)


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


if __name__ == "__main__":
    unittest.main()


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
        js = (ROOT / "adb-scrcpy" / "phone-touch.js").read_text()
        found = dict(re.findall(r"(PHONE_\w+): '([^']+)'", re.search(r"const DEFAULTS = \{([^}]*)\}", js).group(1)))
        self.assertEqual(found, pt.DEFAULTS)
        for key, value in pt.DEFAULTS.items():
            self.assertIn(value, pt.CHOICES[key])
        self.assertIn('PHONE_MAX_SIZE:-1024', (ROOT / "adb-scrcpy" / "phone").read_text())
        self.assertIn('PHONE_BIT_RATE:-2M', (ROOT / "adb-scrcpy" / "phone").read_text())

    def test_reset_keeps_other_lines(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            conf = Path(d) / "phone.conf"
            conf.write_text('PHONE_NAME="x"\nPHONE_MAX_FPS=120\n')
            pt.reset_conf(conf)
            self.assertEqual(conf.read_text(), 'PHONE_NAME="x"\n')
