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
