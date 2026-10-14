"""lib/i18n.py and dev/i18n.py: .po files are read as gettext reads them (contexts, plurals,
multi-line text, fuzzy entries skipped), the language follows the usual variables with English
as the fallback, and the template holds both the marked code text and the manifests' text."""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import i18n  # noqa: E402

PO = textwrap.dedent('''\
    msgid ""
    msgstr ""
    "Language: ru\\n"
    "Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\\n"

    #: gui/frame-tweaks-gui.py:1
    msgid "Refresh"
    msgstr "Обновить"

    msgctxt "button"
    msgid "Open"
    msgstr "Открыть"

    #, fuzzy
    msgid "Close"
    msgstr "Закрыть?"

    msgid ""
    "A long "
    "text"
    msgstr ""
    "Длинный "
    "текст"

    msgid "%d tweak"
    msgid_plural "%d tweaks"
    msgstr[0] "%d твик"
    msgstr[1] "%d твика"
    msgstr[2] "%d твиков"

    msgid "Untranslated"
    msgstr ""
    ''')


class Reading(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [p.unlink() for p in self.d.iterdir()] and self.d.rmdir())
        (self.d / "ru.po").write_text(PO, encoding="utf-8")
        self.cat = i18n.Catalogue(["ru_RU", "ru"], self.d)

    def test_messages(self):
        self.assertEqual(self.cat.language, "ru")
        self.assertEqual(self.cat.gettext("Refresh"), "Обновить")
        self.assertEqual(self.cat.gettext("Open", "button"), "Открыть")
        self.assertEqual(self.cat.gettext("Open"), "Open")                 # (other context)
        self.assertEqual(self.cat.gettext("Close"), "Close")               # fuzzy: not used
        self.assertEqual(self.cat.gettext("A long text"), "Длинный текст")
        self.assertEqual(self.cat.gettext("Untranslated"), "Untranslated")

    def test_plurals(self):
        forms = [self.cat.ngettext("%d tweak", "%d tweaks", n) % n for n in (1, 3, 5, 21)]
        self.assertEqual(forms, ["1 твик", "3 твика", "5 твиков", "21 твик"])

    def test_no_catalogue_is_english(self):
        cat = i18n.Catalogue(["de"], self.d)
        self.assertIsNone(cat.language)
        self.assertEqual(cat.ngettext("%d tweak", "%d tweaks", 2) % 2, "2 tweaks")


class Language(unittest.TestCase):
    def test_usual_variables(self):
        with mock.patch.dict(os.environ, {"LANGUAGE": "pt_BR:de", "LANG": "fr_FR.UTF-8"}, clear=True):
            self.assertEqual(i18n.wanted_languages(), ["pt_BR", "pt", "de"])     # LANGUAGE wins
        with mock.patch.dict(os.environ, {"LANG": "fr_FR.UTF-8"}, clear=True):
            self.assertEqual(i18n.wanted_languages(), ["fr_FR", "fr"])
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANGUAGE": "de", "LANG": "C.UTF-8"}, clear=True):
            self.assertEqual(i18n.wanted_languages(), ["de"])


class Template(unittest.TestCase):
    def test_up_to_date_and_complete(self):
        r = subprocess.run([sys.executable, str(ROOT / "dev/i18n.py"), "check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        pot = (ROOT / "locale/frame-tweaks.pot").read_text()
        self.assertIn('msgid "Refresh"', pot)                               # marked in the code
        self.assertIn('msgid "Arrow Pad"', pot)                             # a tweak's title
        self.assertIn('msgid "VR environment"', pot)                        # a category
        self.assertNotIn('msgid "1.5"', pot)                                # nothing to translate

    def test_manifest_text_is_translated_on_load(self):
        """A tweak's title comes out translated (sft.load), its id and files unchanged."""
        d = Path(tempfile.mkdtemp())
        (d / "de.po").write_text('msgid ""\nmsgstr ""\n\nmsgid "Arrow Pad"\nmsgstr "Pfeiltasten"\n', encoding="utf-8")
        import sft
        with mock.patch.object(i18n, "CATALOGUE", i18n.Catalogue(["de"], d)):
            c = next(c for c in sft.load(refresh=True)["components"] if c["id"] == "arrowpad")
            self.assertEqual(c["title"], "Pfeiltasten")
        sft.load(refresh=True)

if __name__ == "__main__":
    unittest.main()
