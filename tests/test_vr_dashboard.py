"""vr-dashboard/sft-dashboard: settings arm/restore and each patch's SteamVR compatibility check."""
import importlib.machinery
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_l = importlib.machinery.SourceFileLoader("sft", str(ROOT / "packs/original/vr-dashboard" / "sft-dashboard"))
sft = importlib.util.module_from_spec(importlib.util.spec_from_loader("sft", _l))
_l.exec_module(sft)
def _patches():
    """Every dashboard patch a tweak installs: install_dashboard_patch NAME FILE in its install.sh."""
    found = {}
    for inst in ROOT.glob("packs/*/*/install.sh"):
        for name, rel in re.findall(r'install_dashboard_patch\s+(\S+)\s+"\$TWEAK_DIR/([^"]+)"', inst.read_text()):
            found[name] = inst.parent / rel
    return found


PATCHES = _patches()
PATCHES_AND_LIB = {**PATCHES, "lib": ROOT / "packs/original/vr-dashboard" / "lib.js"}


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
    def test_every_patch_is_found(self):
        self.assertGreaterEqual(set(PATCHES), {"curvature", "float-return", "float-grab", "scroll-strips",
                                               "phone-rotate", "phone-touch"})
        for path in PATCHES.values():
            self.assertTrue(path.is_file(), path)

    def test_each_patch_detects_missing_markers(self):
        for name, path in PATCHES_AND_LIB.items():
            req = sft.requires(path)
            self.assertGreater(len(req), 2, name)                  # its own "// requires:" lines
            self.assertEqual(sft.missing(path, "".join(req.values())), [], name)
            self.assertEqual(sorted(sft.missing(path, "nothing here")), sorted(req), name)
            self.assertEqual(sft.missing(path, None), ["SteamVR's dashboard files"])

    @unittest.skipUnless(sft.DASHBOARD.is_dir(), "SteamVR isn't installed here")
    def test_patches_match_the_installed_steamvr(self):
        code = sft.dashboard_code()
        for name, path in PATCHES_AND_LIB.items():
            self.assertEqual(sft.missing(path, code), [], name)


class SaveConfig(unittest.TestCase):
    def test_only_installed_patches_and_small_objects(self):
        with tempfile.TemporaryDirectory() as d:
            conf = Path(d) / "conf"
            with mock.patch.object(sft, "CONF_DIR", conf), \
                 mock.patch.object(sft, "patches", return_value={"scroll-strips": Path("x.js")}):
                sft.save_config({"name": "scroll-strips", "config": {"color": 0.5}})
                self.assertEqual(json.loads((conf / "scroll-strips.json").read_text()), {"color": 0.5})
                sft.save_config({"name": "../evil", "config": {"a": 1}})
                sft.save_config({"name": "other", "config": {"a": 1}})
                sft.save_config({"name": "scroll-strips", "config": ["not", "an", "object"]})
                sft.save_config({"name": "scroll-strips", "config": {"big": "x" * 5000}})
                self.assertEqual(sorted(p.name for p in conf.iterdir()), ["scroll-strips.json"])
                self.assertEqual(json.loads((conf / "scroll-strips.json").read_text()), {"color": 0.5})


if __name__ == "__main__":
    unittest.main()
