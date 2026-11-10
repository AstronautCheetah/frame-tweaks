"""dev/i18n-terms.py: which phrases of ours name something in other software, and reading Steam's
and SteamVR's own translations (made up here; the real ones are on a Steam Frame)."""
import contextlib
import io
import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
terms = load_script(ROOT / "dev/i18n-terms.py", "terms")


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

    def asar(self, name, files):
        """name: an Electron archive of {path: bytes} laid out as asar writes one (the index's
        offsets as strings, padded to 4 bytes, one entry marked unpacked that isn't in it)."""
        index, blobs, offset = {"files": {}}, b"", 0
        for path, data in files.items():
            folder = index
            *parents, leaf = path.split("/")
            for p in parents:
                folder = folder["files"].setdefault(p, {"files": {}})
            folder["files"][leaf] = {"offset": str(offset), "size": len(data)}
            blobs += data
            offset += len(data)
        index["files"]["native.node"] = {"offset": "0", "size": 3, "unpacked": True}
        js = json.dumps(index).encode()
        padded = (len(js) + 3) // 4 * 4
        header = struct.pack("<4I", 4, padded + 8, padded + 4, len(js)) + js.ljust(padded, b"\0")
        (self.d / name).write_bytes(header + blobs)
        return self.d / name

    def test_asar(self):
        contents = {"i18n/en-US.json": b'{"k": "Apply changes"}', "i18n/dynamic/fr-FR.json": b'{"k": "Appliquer"}',
                    "top": b"x"}
        archive = self.asar("a.asar", contents)
        files = terms.asar(archive)
        self.assertEqual(set(files), set(contents))   # (the unpacked entry left out)
        with open(archive, "rb") as f:
            for path, (offset, size) in files.items():
                f.seek(offset)
                self.assertEqual(f.read(size), contents[path], path)

    def test_claude_loose_then_archives(self):
        loose = self.d / "loose"
        loose.mkdir()
        (loose / "en-US.json").write_text(json.dumps({"a": "Made by", "n": 1}))
        (loose / "es-419.json").write_text(json.dumps({"a": "Creado por", "n": 1}))
        archive = self.asar("app.asar", {
            "i18n/en-US.json": json.dumps({"b": "Copy image", "c": "Text copied"}).encode(),
            "i18n/es-419.json": json.dumps({"b": "Copiar imagen"}).encode(),
            "i18n/nl.json": json.dumps({"b": "Kopieer afbeelding", "c": "Tekst gekopieerd"}).encode(),
            "other/fr-FR.json": b'{"b": "no English beside it"}'})
        with mock.patch.object(terms, "CLAUDE_LOOSE", [loose, self.d / "gone"]), \
                mock.patch.object(terms, "CLAUDE_ASARS", [archive, self.d / "gone.asar"]):
            self.assertEqual(list(terms.claude("es_419")), [("Made by", "Creado por"), ("Copy image", "Copiar imagen")])
            self.assertEqual(list(terms.claude("nl_BE")),      # (no Belgian Dutch: Dutch)
                             [("Copy image", "Kopieer afbeelding"), ("Text copied", "Tekst gekopieerd")])
            self.assertEqual(list(terms.claude("fr")), [])


class Terms(unittest.TestCase):
    TABLE = {"Apply Changes": [("Aplicar cambios", "KDE", 2)],
             "1 second": [("1 segundo", "Steam", 3), ("1\u00a0segundo", "Android", 1), ("1\u202fsegundo", "KDE", 1),
                          ("1 seg", "KDE", 1)],
             "Caps Lock": [("Bloq Mayús", "Claude Desktop", 2)], "caps lock": [("Bloq Mayús", "KDE", 1)]}

    def rows(self, msgids, here=None):
        with mock.patch.object(terms, "official", return_value=(self.TABLE, here or {"KDE": 1})), \
                mock.patch.object(terms, "template_msgids", return_value=msgids):
            return terms.terms("es_419")[0]

    def test_case_insensitive_like_lookup(self):
        rows = self.rows(["Apply changes", "Caps Lock"])
        self.assertEqual([(r[0], r[1], r[2]) for r in rows],
                         [("Apply changes", "Aplicar cambios", "KDE"), ("Caps Lock", "Bloq Mayús", "Claude Desktop")])
        self.assertEqual(rows[1][3], "")              # (the same wording from KDE: no alternative)

    def test_nbsp_is_the_same_wording(self):
        (en, tr, _src, alts, used), = self.rows(["1 second"])
        self.assertEqual((en, tr, alts, used), ("1 second", "1 segundo", "1 seg (KDE)", ["1 second"]))
        self.assertEqual(terms.same("1\u00a0segundo"), "1 segundo")

    def test_not_written_without_a_source(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / "locale/glossary").mkdir(parents=True)
        here = {"SteamVR": 3, "Claude Desktop": 0, "KDE": 0}
        with mock.patch.object(terms, "ROOT", root), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(terms, "terms", return_value=([("Caps Lock", "Bloq Mayús", "KDE", "", ["x"])], here)):
            with mock.patch.object(sys, "argv", ["i18n-terms.py", "es_419"]), self.assertRaises(SystemExit) as e:
                terms.main()
            self.assertIn("Claude Desktop, KDE", str(e.exception))
            self.assertFalse((root / "locale/glossary/es_419.terms.tsv").exists())
            with mock.patch.object(sys, "argv", ["i18n-terms.py", "es_419", "--allow-missing"]):
                terms.main()
            self.assertIn("Caps Lock\tBloq Mayús\tKDE", (root / "locale/glossary/es_419.terms.tsv").read_text())


if __name__ == "__main__":
    unittest.main()
