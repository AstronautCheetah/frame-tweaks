"""curvature/sft-curvature: settings arm/restore and the SteamVR compatibility check."""
import importlib.machinery
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sft = importlib.machinery.SourceFileLoader("sft", str(ROOT / "curvature" / "sft-curvature")).load_module()


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
    def test_detects_missing_markers(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.js").write_text("".join(sft.EXPECTED.values()))
            with mock.patch.object(sft, "DASHBOARD", Path(d)):
                self.assertEqual(sft.check_dashboard(), [])
                (Path(d) / "a.js").write_text("nothing here")
                self.assertEqual(sorted(sft.check_dashboard()), sorted(sft.EXPECTED))


if __name__ == "__main__":
    unittest.main()
