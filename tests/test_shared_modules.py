"""lib/ftconf.py (settings files and logs) and lib/vrkit.py (poses, haptic pulses and grips): the
modules the installed programs share (lib/common.sh install_i18n puts them beside i18n.py)."""
import json
import math
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import ftconf  # noqa: E402
import vrkit  # noqa: E402


class Settings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)

    def test_json_not_an_object_reads_as_none(self):
        f = self.d / "a.json"
        for text in ("null", "[1, 2]", '{"half', ""):
            f.write_text(text)
            self.assertEqual(ftconf.read_json(f), {}, text)
        self.assertEqual(ftconf.read_json(self.d / "missing.json"), {})

    def test_json_update_keeps_other_keys_and_drops(self):
        f = self.d / "sub/a.json"
        ftconf.update_json(f, {"a": 1, "old": 2})
        self.assertEqual(ftconf.update_json(f, {"b": 3}, drop=("old",)), {"a": 1, "b": 3})
        self.assertEqual(json.loads(f.read_text()), {"a": 1, "b": 3})
        self.assertEqual(os.listdir(f.parent), ["a.json"])               # (no temporary file left)

    def test_write_keeps_permissions_and_writes_through_a_link(self):
        real = self.d / "real.conf"
        real.write_text("x\n")
        real.chmod(0o600)
        link = self.d / "link.conf"
        link.symlink_to(real)
        ftconf.write_text(link, "y\n")
        self.assertTrue(link.is_symlink())
        self.assertEqual(real.read_text(), "y\n")
        self.assertEqual(real.stat().st_mode & 0o777, 0o600)

    def test_shell_read_as_source_would(self):
        f = self.d / "a.conf"
        f.write_text("# a comment\nA=1\nB='two words'\nC=\"x\"\nnot a setting\nD='it'\"'\"'s'\n")      # (shlex.quote("it's"))
        self.assertEqual(ftconf.read_shell(f), {"A": "1", "B": "two words", "C": "x", "D": "it's"})

    def test_shell_set_keeps_other_lines_quotes_and_drops(self):
        f = self.d / "a.conf"
        f.write_text("# mine\nA=1\nB=2\nA=dup\nKEEP=yes\n")
        ftconf.set_shell(f, {"A": "two words", "NEW": 5}, drop=("B",))
        self.assertEqual(f.read_text(), "# mine\nA='two words'\nKEEP=yes\nNEW=5\n")
        self.assertEqual(ftconf.read_shell(f)["A"], "two words")

    def test_log_rotates(self):
        log = self.d / "logs/x.log"
        ftconf.append_log(log, "first", max_bytes=10)
        ftconf.append_log(log, "second", max_bytes=10)          # (over 10 bytes: rotated first)
        self.assertIn("first", (self.d / "logs/x.log.1").read_text())
        self.assertIn("second", log.read_text())
        self.assertNotIn("first", log.read_text())
        ftconf.append_log(log, "ms", stamp="%H:%M:%S.ms")
        self.assertRegex(log.read_text().splitlines()[-1], r"^\d\d:\d\d:\d\d\.\d{3} ms$")

    def test_log_never_raises(self):
        ftconf.append_log(Path("/proc/no/such/place.log"), "x")


class VR(unittest.TestCase):
    ROT = [[0, -1, 0, 1.0], [1, 0, 0, 2.0], [0, 0, 1, 3.0]]     # 90° about z, then moved

    def test_inverse_and_relative(self):
        ident = vrkit.rigid_mul(vrkit.rigid_inv(self.ROT), self.ROT)
        for r in range(3):
            for c in range(4):
                self.assertAlmostEqual(ident[r][c], 1.0 if r == c else 0.0)
        b = vrkit.rigid_mul(self.ROT, [[1, 0, 0, 0.5], [0, 1, 0, 0], [0, 0, 1, 0]])
        rel = vrkit.relative(self.ROT, b)
        self.assertAlmostEqual(rel[0][3], 0.5)

    def test_direct_pulse(self):
        vr = mock.Mock(k_unTrackedDeviceIndexInvalid=-1)
        system = mock.Mock()
        self.assertFalse(vrkit.direct_pulse(vr, system, -1, 1000))
        self.assertFalse(vrkit.direct_pulse(vr, system, None, 1000))
        self.assertTrue(vrkit.direct_pulse(vr, system, 3, 9000.7))
        system.triggerHapticPulse.assert_called_once_with(3, 0, 3999)      # (at most 3999 µs)
        self.assertEqual(vrkit.TICK, {"hover": 1000, "press": 3999})

    @staticmethod
    def grip_vr(angle):
        """openvr as GripReader sees it: the left hand is device 1, the right 2, and each grip
        part is turned angle[hand] degrees from its rest pose."""
        def turned(deg):
            c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            return types.SimpleNamespace(mTrackingToComponentRenderModel=types.SimpleNamespace(
                m=[[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0]]))
        system = mock.Mock(isTrackedDeviceConnected=lambda d: True,
                           getTrackedDeviceIndexForControllerRole=lambda role: role)
        models = mock.Mock(getComponentStateForDevicePath=lambda m, part, path, mode: (True, turned(angle[path])),
                           getComponentState=lambda m, part, state, mode: (True, turned(0)))
        inp = mock.Mock(getInputSourceHandle=lambda path: path.rsplit("/", 1)[1])
        return mock.Mock(k_unTrackedDeviceIndexInvalid=-1, TrackedControllerRole_LeftHand=1,
                         TrackedControllerRole_RightHand=2, VRSystem=lambda: system,
                         VRRenderModels=lambda: models, VRInput=lambda: inp)

    def test_grip_squeezed_while_paused_is_held_not_a_squeeze(self):
        """Arrow Pad and Screen snip read grips only while a laser is on them: one squeezed
        meanwhile (carrying a window with Float grab, say) mustn't grab the panel the laser reaches."""
        angle = {"left": 0.0, "right": 0.0}
        g = vrkit.GripReader(self.grip_vr(angle))
        self.assertEqual(g.poll(), [])                              # (armed by a released sample)
        angle["right"] = 5.0
        self.assertEqual(g.poll(), [(1, False, False), (2, True, True)])     # read: a squeeze
        angle["right"] = 0.0
        g.poll()
        g.pause()
        angle["right"] = 5.0                                        # squeezed, unread
        self.assertEqual(g.poll(), [(1, False, False), (2, True, False)])    # held, no squeeze
        self.assertEqual(g.poll()[1], (2, True, False))
        angle["right"] = 0.0
        g.poll()
        angle["right"] = 5.0
        self.assertEqual(g.poll()[1], (2, True, True))              # a new one is
        angle["right"] = 0.0
        g.poll()
        g.pause()                                                   # released while unread
        angle["right"] = 5.0
        g.pause()
        angle["right"] = 0.0
        self.assertEqual(g.poll()[1], (2, False, False))
        angle["right"] = 5.0
        self.assertEqual(g.poll()[1], (2, True, True))


if __name__ == "__main__":
    unittest.main()
