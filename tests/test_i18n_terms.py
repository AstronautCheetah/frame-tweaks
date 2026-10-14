"""dev/i18n-terms.py: which phrases of ours name something in other software, and reading Steam's
and SteamVR's own translations (made up here; the real ones are on a Steam Frame)."""
import importlib.machinery
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_l = importlib.machinery.SourceFileLoader("terms", str(ROOT / "dev/i18n-terms.py"))
terms = importlib.util.module_from_spec(importlib.util.spec_from_loader("terms", _l))
_l.exec_module(terms)


class Phrases(unittest.TestCase):
    def test_names_not_sentences(self):
        p = terms.phrases('"Float in World" also picks the window up; open System Settings, then **Lock now**.')
        self.assertIn("Float in World", p)
        self.assertIn("System Settings", p)
        self.assertIn("Lock now", p)
        self.assertNotIn("also picks", p)
        self.assertIn("Apply changes", terms.phrases("Apply changes"))     # a whole short label
        self.assertEqual(terms.clean("&Change Password..."), "Change Password")


class Sources(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d)

    def test_steamvr_and_steam(self):
        (self.d / "dashboard_english.json").write_text(json.dumps({"FloatInWorld": "Float in World"}))
        (self.d / "dashboard_latam.json").write_text(json.dumps({"FloatInWorld": "Flotar en el mundo"}))
        js = 'x.push([[1],{2:(e=>{e.exports=JSON.parse(`{"A":"%s","B":"say \\\\"hi\\\\""}`)})}])'
        (self.d / "steamui_english-json.js").write_text(js % "Close")
        (self.d / "steamui_latam-json.js").write_text(js % "\\xA1Cerrar!")
        with mock.patch.object(terms, "STEAMVR", self.d), mock.patch.object(terms, "STEAMUI", self.d):
            self.assertEqual(list(terms.steamvr("es_419")), [("Float in World", "Flotar en el mundo")])
            self.assertEqual(dict(terms.steam("es_419")), {"Close": "¡Cerrar!", 'say "hi"': 'say "hi"'})


if __name__ == "__main__":
    unittest.main()
