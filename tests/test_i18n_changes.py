"""English changes waiting for translation (dev/i18n.py: locale/CHANGES.md, todo, export's "was").
Translations are done just before a release; in between, each extract notes what it changed, so
translators adjust the old translation instead of hunting for the change."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402

tool = load_script(ROOT / "dev/i18n.py", "i18n_tool_changes")


def pot(*entries):
    """A template: (files, msgid) or (files, msgid, context)."""
    out = ['msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', ""]
    for e in entries:
        out.append("#: " + e[0])
        if len(e) > 2:
            out.append(f'msgctxt "{e[2]}"')
        out += [f'msgid "{e[1]}"', 'msgstr ""', ""]
    return "\n".join(out)


def collected(*entries):
    """collect()'s {(context, msgid, plural): [file:line]} for (file:line, msgid[, context])."""
    return {(e[2] if len(e) > 2 else None, e[1], None): [e[0]] for e in entries}


class Changes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.locale = Path(self.tmp.name) / "locale"
        self.locale.mkdir()
        p = mock.patch.object(tool, "LOCALE", self.locale)
        p.start()
        self.addCleanup(p.stop)

    def po(self, lang, translations, gone=()):
        """lang.po: {msgid: translation}; gone: removed texts kept as #~ (with their translation)."""
        out = ['msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', ""]
        for m, t in translations.items():
            out += [f'msgid "{m}"', f'msgstr "{t}"', ""]
        for m, t in gone:
            out += [f'#~ msgid "{m}"', f'#~ msgstr "{t}"', ""]
        (self.locale / f"{lang}.po").write_text("\n".join(out))

    def log(self):
        return [(e["was"], e["now"], e["where"]) for e in tool.read_changes()]

    def test_a_changed_text_is_logged_with_what_it_was_and_where(self):
        self.po("fr", {"Open the file": "Ouvrir le fichier", "Close": "Fermer"})
        old = pot(("gui/x.py", "Open the file"), ("gui/x.py", "Close"))
        tool.log_changes(old, collected(("gui/x.py:12", "Open the files"), ("gui/x.py:20", "Close"),
                                        ("gui/y.py:3", "Quit")), today="2026-10-17")
        self.assertEqual(sorted(self.log(), key=lambda e: e[1]), [("Open the file", "Open the files", "gui/x.py:12"),
                                                                (None, "Quit", "gui/y.py:3")])
        text = tool.changes_file().read_text()
        self.assertIn("## 2026-10-17\n- Changed in `gui/x.py:12`\n  - was: \"Open the file\"\n"
                      "  - now: \"Open the files\"", text)
        self.assertIn("- New in `gui/y.py:3`", text)

    def test_unrelated_texts_in_other_files_arent_a_change(self):
        self.po("fr", {})
        old = pot(("gui/x.py", "Open the file"))
        tool.log_changes(old, collected(("gui/y.py:3", "Open the files")))
        self.assertEqual(self.log(), [(None, "Open the files", "gui/y.py:3")])

    def test_changed_again_keeps_what_it_first_was_and_changed_back_goes(self):
        self.po("fr", {"Save": "Enregistrer"})
        tool.log_changes(pot(("gui/x.py", "Save")), collected(("gui/x.py:1", "Save it")))
        tool.log_changes(pot(("gui/x.py", "Save it")), collected(("gui/x.py:1", "Save it now")))
        self.assertEqual(self.log(), [("Save", "Save it now", "gui/x.py:1")])
        tool.log_changes(pot(("gui/x.py", "Save it now")), collected(("gui/x.py:1", "Save")))
        self.assertEqual(self.log(), [])

    def test_a_waiting_text_thats_gone_goes(self):
        self.po("fr", {})
        tool.log_changes(pot(), collected(("gui/x.py:1", "Brand new")))
        tool.log_changes(pot(("gui/x.py", "Brand new")), {})
        self.assertEqual(self.log(), [])

    def test_an_entry_goes_once_every_language_has_it(self):
        self.po("fr", {})
        self.po("nl_BE", {})
        tool.log_changes(pot(), collected(("gui/x.py:1", "Quit"), ("gui/x.py:2", "Help")))
        self.po("fr", {"Quit": "Quitter", "Help": "Aide"})
        tool.tidy_changes()
        self.assertEqual(len(self.log()), 2)                   # (Flemish still lacks them)
        self.po("nl_BE", {"Quit": "Afsluiten"})
        tool.tidy_changes()
        self.assertEqual(self.log(), [(None, "Help", "gui/x.py:2")])

    def test_export_hands_over_what_it_was_and_its_translation(self):
        self.po("fr", {}, gone=[("Open the file", "Ouvrir le fichier")])
        tool.log_changes(pot(("gui/x.py", "Open the file")), collected(("gui/x.py:1", "Open the files")))
        d = Path(self.tmp.name) / "batch"
        with mock.patch.object(tool, "template", lambda: pot(("gui/x.py", "Open the files"), ("gui/x.py", "Quit"))):
            tool.export("fr", d)
            rows = {r["msgid"]: r for r in json.loads((d / "part-01.json").read_text())}
            self.assertEqual((rows["Open the files"]["was"], rows["Open the files"]["was_translation"]),
                             ("Open the file", "Ouvrir le fichier"))
            self.assertNotIn("was", rows["Quit"])
            self.assertEqual(tool.todo(pot(("gui/x.py", "Open the files"), ("gui/x.py", "Quit"))),
                             [("fr", 1, 1, 0)])                # (1 new, 1 changed, none to review)

    def test_the_log_reads_back_what_it_wrote(self):
        log = [{"date": "2026-10-17", "where": "a.sh:3", "ctx": "key legend", "was": 'Say "hi"\nnow',
                "now": "Tab", "plural": None}]
        tool.write_changes(log)
        self.assertEqual(tool.read_changes(), log)
        tool.write_changes([])
        self.assertIn("Nothing waiting", tool.changes_file().read_text())
        self.assertEqual(tool.read_changes(), [])


if __name__ == "__main__":
    unittest.main()
