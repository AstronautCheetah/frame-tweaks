"""vr-dashboard/sft-dashboard: settings arm/restore and each patch's SteamVR compatibility check."""
import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_l = importlib.machinery.SourceFileLoader("sft", str(ROOT / "vr-dashboard" / "sft-dashboard"))
sft = importlib.util.module_from_spec(importlib.util.spec_from_loader("sft", _l))
_l.exec_module(sft)
PATCHES = {"curvature": ROOT / "curvature" / "patch.js", "float-return": ROOT / "float-return" / "patch.js",
           "float-grab": ROOT / "float-grab" / "patch.js",
           "scroll-strips": ROOT / "scroll-strips" / "patch.js",
           "phone-rotate": ROOT / "adb-scrcpy" / "patch.js", "phone-touch": ROOT / "adb-scrcpy" / "phone-touch.js"}


class ArmRestore(unittest.TestCase):
    def run_case(self, before):
        with tempfile.TemporaryDirectory() as d:
            settings, state = Path(d) / "steamvr.vrsettings", Path(d) / "state" / "prev"
            settings.write_text(json.dumps(before))
            with mock.patch.object(sft, "SETTINGS", settings), mock.patch.object(sft, "STATE", state):
                sft.arm()
                self.assertIs(json.loads(settings.read_text())["VRWebHelper"]["DebuggerEnabled"], True)
                sft.arm()                                   # twice: still restores the original
                sft.restore()
                self.assertFalse(state.exists())
                return json.loads(settings.read_text())

    def test_absent_key_is_removed_again(self):
        self.assertEqual(self.run_case({"steamvr": {"a": 1}}), {"steamvr": {"a": 1}})

    def test_false_is_put_back(self):
        after = self.run_case({"VRWebHelper": {"DebuggerEnabled": False, "x": 1}})
        self.assertEqual(after, {"VRWebHelper": {"DebuggerEnabled": False, "x": 1}})

    def test_true_by_user_is_left_alone(self):
        self.assertEqual(self.run_case({"VRWebHelper": {"DebuggerEnabled": True}}),
                         {"VRWebHelper": {"DebuggerEnabled": True}})


class DashboardCheck(unittest.TestCase):
    def test_each_patch_detects_missing_markers(self):
        for name, path in PATCHES.items():
            req = sft.requires(path)
            self.assertGreater(len(req), 2, name)                  # its own "// requires:" lines
            self.assertEqual(sft.missing(path, "".join(req.values())), [], name)
            self.assertEqual(sorted(sft.missing(path, "nothing here")), sorted(req), name)
            self.assertEqual(sft.missing(path, None), ["SteamVR's dashboard files"])

    @unittest.skipUnless(sft.DASHBOARD.is_dir(), "SteamVR isn't installed here")
    def test_patches_match_the_installed_steamvr(self):
        code = sft.dashboard_code()
        for name, path in PATCHES.items():
            self.assertEqual(sft.missing(path, code), [], name)


if __name__ == "__main__":
    unittest.main()
