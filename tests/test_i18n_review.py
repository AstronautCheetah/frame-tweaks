"""dev/i18n.py's "needs review" mark: a translation imported with --needs-review (a machine's,
say) is used like any other, counted apart (stats, report), kept by update, exported with
--review, and cleared by an import with --reviewed."""
import json
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

tool = load_script(ROOT / "dev/i18n.py", "i18n_tool")

POT = '''msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

#: gui/x.py:1
msgid "Open"
msgstr ""

#: gui/x.py:2
msgid "Close"
msgstr ""'''


class NeedsReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.locale = Path(self.tmp.name) / "locale"
        self.locale.mkdir()
        self.po = self.locale / "es_419.po"
        self.po.write_text(POT + "\n")
        for name, value in (("LOCALE", self.locale), ("template", lambda: POT)):
            p = mock.patch.object(tool, name, value)
            p.start()
            self.addCleanup(p.stop)

    def answer(self, d, answers):
        d.mkdir(exist_ok=True)
        tool.export("es_419", d, every=True)
        rows = json.loads((d / "part-01.json").read_text())
        (d / "part-01.es_419.json").write_text(json.dumps({str(r["id"]): answers[r["msgid"]]
                                                           for r in rows if r["msgid"] in answers}))

    def test_marked_shown_counted_kept_and_cleared(self):
        d = Path(self.tmp.name) / "batch"
        self.answer(d, {"Open": "Abrir", "Close": "Cerrar"})
        tool.import_("es_419", d, "add")
        text = self.po.read_text()
        self.assertEqual(i18n.parse_po(text)[(None, "Open")], ["Abrir"])          # shown
        self.assertEqual(tool.needs_review(text), {(None, "Open"), (None, "Close")})
        self.assertEqual(tool.progress(POT)[0][:4], ("es_419", 2, 2, 2))
        self.assertIn("2 need review", tool.report(POT))
        tool.update(self.po, POT)                                                  # (kept)
        self.assertEqual(len(tool.needs_review(self.po.read_text())), 2)
        self.assertTrue(self.po.read_text().split("\n\n")[1].startswith("# needs review\n#: gui/x.py:1"))
        r = Path(self.tmp.name) / "review"
        r.mkdir()
        tool.export("es_419", r, review=True)
        self.assertEqual([row["current"] for row in json.loads((r / "part-01.json").read_text())], ["Abrir", "Cerrar"])
        self.answer(d, {"Open": "Abrir"})
        tool.import_("es_419", d, "clear")
        self.assertEqual(tool.needs_review(self.po.read_text()), {(None, "Close")})
        self.answer(d, {"Close": "Cerrar"})
        tool.import_("es_419", d)                                                   # (no flag: mark left as it is)
        self.assertEqual(tool.needs_review(self.po.read_text()), {(None, "Close")})

    def test_review_of_a_language_not_started_says_so(self):
        with self.assertRaises(SystemExit) as e:
            tool.export("pt_BR", Path(self.tmp.name) / "review", review=True)
        self.assertEqual(str(e.exception.code), "no locale/pt_BR.po: nothing of pt_BR's to review")

    def test_untranslated_listed_in_the_report(self):
        report = tool.report(POT)
        self.assertIn("es_419: 0 of 2 translated", report)
        self.assertIn("- `Open`", report)


if __name__ == "__main__":
    unittest.main()
