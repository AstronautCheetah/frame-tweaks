"""lib/sft.py: the settings, hidden rows and details shared by the installer window and
./install.sh, and that the VR gear panels still offer the same choices."""
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
sys.path.insert(0, str(ROOT / "lib"))
import i18n  # noqa: E402
import sft  # noqa: E402

pt = load_script(ROOT / "packs/original/adb-scrcpy" / "phone-touch", "phone_touch")


def values(cid):
    return {key: [v for _, v in choices] for key, _, choices, _ in sft.SETTINGS[cid]["options"]}


class SameChoicesEverywhere(unittest.TestCase):
    def test_android_mirror_gear_and_helper(self):
        self.assertEqual({k: list(v) for k, v in pt.CHOICES.items()}, values("adb-scrcpy"))
        self.assertEqual(pt.DEFAULTS, sft.defaults("adb-scrcpy"))
        js = (ROOT / "packs/original/adb-scrcpy" / "phone-touch.js").read_text()
        for key, vals in values("adb-scrcpy").items():
            for v in vals:
                self.assertIn(f"'{v}'", js, f"{key}={v} missing from the VR panel")

    def test_scroll_strips_gear(self):
        js = (ROOT / "packs/original/scroll-strips" / "patch.js").read_text()
        swatches = [float(x) for x in re.search(r"const SWATCHES = \[([^\]]*)\]", js).group(1).split(",")]
        self.assertEqual(swatches, [v for v in values("scroll-strips")["color"] if v != "tint"])
        for key, cm in (("thickness", r"'thickness', \[([^\]]*)\]"), ("gap", r"'gap', \[([^\]]*)\]"),
                        ("back", r"'back', \[([^\]]*)\]")):
            listed = [float(x) / 100 for x in re.search(cm, js).group(1).split(",")]
            self.assertEqual([round(v, 4) for v in listed], [round(v, 4) for v in values("scroll-strips")[key]], key)
        d = re.search(r"const DEFAULTS = \{([^}]*)\}", js).group(1)
        d = re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", d))      # (JavaScript's booleans)
        self.assertEqual(eval("{" + re.sub(r"(\w+):", r"'\1':", d) + "}"), sft.defaults("scroll-strips"))


class SpeechLanguages(unittest.TestCase):
    """The Speech engine's Language choices are voices.tsv's languages (dev/speech-voices.py),
    each with a Piper voice file, two SHA256s and an eSpeak NG voice."""
    def test_same_languages(self):
        rows = [l.split("\t") for l in (ROOT / "packs/original/speech/voices.tsv").read_text().splitlines()
                if l and not l.startswith("#")]
        self.assertTrue(all(len(r) == 6 and re.fullmatch(r"[0-9a-f]{64}", r[3]) and re.fullmatch(r"[0-9a-f]{64}", r[4])
                            and r[2].endswith(".onnx") for r in rows))
        self.assertEqual([r[0] for r in rows], values("speech")["SPEECH_LANGUAGE"])
        self.assertEqual(rows[0][0], sft.defaults("speech")["SPEECH_LANGUAGE"])


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

    def test_shell_values_can_be_sourced_and_read_back(self):
        """A value with a space is quoted, so sourcing the file gives it whole (not a command
        "morning"); a number a manifest lists unquoted reads back as the one chosen."""
        f = Path(self.d.name) / "mine.conf"
        sft.SETTINGS["mine"] = {"file": f, "format": "shell", "options": [
            ("GREETING", "Greeting", [("Hello", "hello"), ("Good morning", "good morning")], "hello"),
            ("SIZE", "Size", [("Small", 720), ("Big", 1280)], 720)]}
        sft.write_settings("mine", {"GREETING": "good morning", "SIZE": 1280})
        self.assertEqual(sft.read_settings("mine"), {"GREETING": "good morning", "SIZE": 1280})
        self.assertEqual(sft.raw_setting("mine", "GREETING"), "good morning")

    def test_json_that_isnt_a_mapping_reads_as_the_defaults(self):
        f = sft.SETTINGS["scroll-strips"]["file"]
        for text in ("null", "[1, 2]", '"x"'):
            f.write_text(text)
            self.assertEqual(sft.read_settings("scroll-strips"), sft.defaults("scroll-strips"), text)

    def test_a_key_is_looked_up_never_run(self):
        """raw_setting sources the file and looks the key up by name: the key isn't shell code."""
        f = sft.SETTINGS["adb-scrcpy"]["file"]
        f.write_text("PHONE_NAME='my phone'\n")
        self.assertEqual(sft.raw_setting("adb-scrcpy", "PHONE_NAME"), "my phone")
        mark = Path(self.d.name) / "ran"
        self.assertEqual(sft.raw_setting("adb-scrcpy", f'X}}"; touch {mark}; echo "${{Y'), "")
        self.assertFalse(mark.exists())


class HiddenRows(unittest.TestCase):
    def test_hide_and_unhide_a_default_hidden_row(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(sft, "HIDDEN", Path(d) / "hidden"), mock.patch.object(sft, "SHOWN", Path(d) / "shown"):
                rows = [{"id": "a", "flags": {"hidden-by-default"}}, {"id": "b", "flags": set()}]
                self.assertEqual(sft.hidden(rows), {"a"})
                sft.set_hidden("a", False)
                sft.set_hidden("b", True)
                self.assertEqual(sft.hidden(rows), {"b"})

    def test_a_group_by_its_english_name_in_another_language(self):
        """./install.sh hide-group "System" (as the README writes it) works in Spanish too, and
        hides the group the window shows (its Spanish name)."""
        self.addCleanup(lambda: sft.load(refresh=True))           # (the English rows again)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "es.po").write_text('msgid ""\nmsgstr ""\n\nmsgid "System"\nmsgstr "Sistema"\n', encoding="utf-8")
            with mock.patch.object(i18n, "CATALOGUE", i18n.Catalogue(["es"], Path(d))), \
                    mock.patch.object(sft, "HIDDEN_CATS", Path(d) / "hidden-categories"), \
                    contextlib.redirect_stdout(io.StringIO()):
                sft.load(refresh=True)
                sft.main(["hide-group", "System"])
                self.assertEqual(sft.read_set(sft.HIDDEN_CATS), {"Sistema"})


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
