"""lib/sft.py: the settings, hidden rows and details shared by the installer window and
./install.sh, and that the VR gear panels still offer the same choices."""
import importlib.machinery
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import sft  # noqa: E402

_l = importlib.machinery.SourceFileLoader("phone_touch", str(ROOT / "packs/official/adb-scrcpy" / "phone-touch"))
pt = importlib.util.module_from_spec(importlib.util.spec_from_loader("phone_touch", _l))
_l.exec_module(pt)


def values(cid):
    return {key: [v for _, v in choices] for key, _, choices, _ in sft.SETTINGS[cid]["options"]}


class SameChoicesEverywhere(unittest.TestCase):
    def test_android_mirror_gear_and_helper(self):
        self.assertEqual({k: list(v) for k, v in pt.CHOICES.items()}, values("adb-scrcpy"))
        self.assertEqual(pt.DEFAULTS, sft.defaults("adb-scrcpy"))
        js = (ROOT / "packs/official/adb-scrcpy" / "phone-touch.js").read_text()
        for key, vals in values("adb-scrcpy").items():
            for v in vals:
                self.assertIn(f"'{v}'", js, f"{key}={v} missing from the VR panel")

    def test_scroll_strips_gear(self):
        js = (ROOT / "packs/official/scroll-strips" / "patch.js").read_text()
        swatches = [float(x) for x in re.search(r"const SWATCHES = \[([^\]]*)\]", js).group(1).split(",")]
        self.assertEqual(swatches, [v for v in values("scroll-strips")["color"] if v != "tint"])
        for key, cm in (("thickness", r"'thickness', \[([^\]]*)\]"), ("gap", r"'gap', \[([^\]]*)\]"),
                        ("back", r"'back', \[([^\]]*)\]")):
            listed = [float(x) / 100 for x in re.search(cm, js).group(1).split(",")]
            self.assertEqual([round(v, 4) for v in listed], [round(v, 4) for v in values("scroll-strips")[key]], key)
        d = re.search(r"const DEFAULTS = \{([^}]*)\}", js).group(1)
        d = re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", d))      # (JavaScript's booleans)
        self.assertEqual(eval("{" + re.sub(r"(\w+):", r"'\1':", d) + "}"), sft.defaults("scroll-strips"))


class ReadWrite(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        spec = {k: dict(v) for k, v in sft.SETTINGS.items()}
        spec["scroll-strips"]["file"] = Path(self.d.name) / "strips.json"
        spec["adb-scrcpy"]["file"] = Path(self.d.name) / "phone.conf"
        p = mock.patch.object(sft, "SETTINGS", spec)
        p.start()
        self.addCleanup(p.stop)

    def test_shell_keeps_other_lines(self):
        f = sft.SETTINGS["adb-scrcpy"]["file"]
        f.write_text('PHONE_NAME="x"\nPHONE_MAX_FPS=120\n')
        sft.write_settings("adb-scrcpy", {"PHONE_MAX_SIZE": "1280"})
        self.assertEqual(f.read_text(), 'PHONE_NAME="x"\nPHONE_MAX_FPS=120\nPHONE_MAX_SIZE=1280\n')
        self.assertEqual(sft.read_settings("adb-scrcpy")["PHONE_MAX_FPS"], "120")
        sft.write_settings("adb-scrcpy", {}, reset=True)
        self.assertEqual(f.read_text(), 'PHONE_NAME="x"\n')
        self.assertEqual(f.read_text(), 'PHONE_NAME="x"\n')

    def test_helper_and_module_write_alike(self):
        a = sft.SETTINGS["adb-scrcpy"]["file"]
        b = Path(self.d.name) / "other.conf"
        for f in (a, b):
            f.write_text("PHONE_NAME=y\nPHONE_MAX_SIZE=800\n")
        sft.write_settings("adb-scrcpy", {"PHONE_MAX_SIZE": "1600", "PHONE_STICK_SPEED": "25"})
        pt.write_conf({"PHONE_MAX_SIZE": "1600", "PHONE_STICK_SPEED": "25"}, b)
        self.assertEqual(a.read_text(), b.read_text())

    def test_json_rejects_unlisted_and_keeps_unknown_keys(self):
        f = sft.SETTINGS["scroll-strips"]["file"]
        f.write_text(json.dumps({"vertical": "left", "future": 1}))
        with self.assertRaises(ValueError):
            sft.write_settings("scroll-strips", {"thickness": 0.07})
        with self.assertRaises(KeyError):
            sft.write_settings("scroll-strips", {"colour": "tint"})
        sft.write_settings("scroll-strips", {"color": sft.parse_value("scroll-strips", "color", "blue")})
        self.assertEqual(json.loads(f.read_text()), {"vertical": "left", "future": 1, "color": 0.67})
        self.assertEqual(sft.parse_value("scroll-strips", "thickness", "2.5"), 0.025)
        sft.write_settings("scroll-strips", {}, reset=True)
        self.assertEqual(json.loads(f.read_text()), {"future": 1})


class HiddenRows(unittest.TestCase):
    def test_hide_and_unhide_a_default_hidden_row(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(sft, "HIDDEN", Path(d) / "hidden"), mock.patch.object(sft, "SHOWN", Path(d) / "shown"):
                rows = [{"id": "a", "flags": {"hidden-by-default"}}, {"id": "b", "flags": set()}]
                self.assertEqual(sft.hidden(rows), {"a"})
                sft.set_hidden("a", False)
                sft.set_hidden("b", True)
                self.assertEqual(sft.hidden(rows), {"b"})


class Experimental(unittest.TestCase):
    """The 🧪 note comes from each tweak's meta, for the window, `info` and the docs alike."""
    def test_dashboard_patches_are_marked_and_plain_installs_are_not(self):
        rows = {c["id"]: c for c in sft.components()}
        for cid in ("vr-dashboard", "curvature", "float-return", "float-grab", "scroll-strips", "adb-scrcpy"):
            self.assertIn("SteamVR", rows[cid]["experimental"], cid)
        for cid in ("cursor", "full-keyboard", "homebrew"):
            self.assertEqual(rows[cid]["experimental"], "", cid)
        self.assertIn("Experimental: ", sft.info("curvature"))


if __name__ == "__main__":
    unittest.main()
