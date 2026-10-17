"""lib/i18n.py and dev/i18n.py: .po files are read as gettext reads them (contexts, plurals,
multi-line text, fuzzy entries skipped), the language follows the usual variables with English
as the fallback, and the template holds both the marked code text and the manifests' text."""
import os
import subprocess
import sys
import json
import shutil
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
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
    def setUp(self):
        p = mock.patch.object(i18n, "keyboard_language", lambda: None)     # (this machine's keyboard: not in the test)
        p.start()
        self.addCleanup(p.stop)

    def test_usual_variables(self):
        with mock.patch.dict(os.environ, {"LANGUAGE": "pt_BR:de", "LANG": "fr_FR.UTF-8"}, clear=True):
            self.assertEqual(i18n.wanted_languages(), ["pt_BR", "pt", "de"])     # LANGUAGE wins
        with mock.patch.dict(os.environ, {"LANG": "fr_FR.UTF-8"}, clear=True):
            self.assertEqual(i18n.wanted_languages(), ["fr_FR", "fr"])
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANGUAGE": "de", "LANG": "C.UTF-8"}, clear=True):
            self.assertEqual(i18n.wanted_languages(), ["de"])

    def test_english_by_any_name(self):
        """FRAME_TWEAKS_LANGUAGE=en_US (or en_GB.UTF-8) is English too, not the keyboard's language."""
        with mock.patch.object(i18n, "keyboard_language", lambda: "de"):
            for value in ("en", "en_US", "en_GB.UTF-8"):
                with mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANGUAGE": value}, clear=True):
                    self.assertEqual(i18n.wanted_languages(), [], value)


class Inherited(unittest.TestCase):
    def test_a_program_speaks_its_parents_language(self):
        """FRAME_TWEAKS_LANG_RESOLVED (the window's or a script's choice) wins over the keyboard,
        except in the installer window itself (INHERIT = False)."""
        none = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, none, True)
        with mock.patch.object(i18n, "keyboard_language", lambda: "de"), mock.patch.object(i18n, "INHERIT", True), \
                mock.patch.object(i18n, "ANNOUNCED", none / "none"):     # (no window open)
            with mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANG_RESOLVED": "es_419"}, clear=True):
                self.assertEqual(i18n.wanted_languages(), ["es_419", "es"])
                with mock.patch.object(i18n, "INHERIT", False):
                    self.assertEqual(i18n.wanted_languages(), ["de"])
            with mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANG_RESOLVED": "en"}, clear=True):
                self.assertEqual(i18n.wanted_languages(), [])


class PreferenceAndAnnouncement(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.d)])
        for name, value in (("PREFERENCE", self.d / "language"), ("ANNOUNCED", self.d / "run/language")):
            p = mock.patch.object(i18n, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_chosen_language_beats_the_keyboard(self):
        with mock.patch.object(i18n, "keyboard_language", lambda: "de"), mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(i18n.wanted_languages(), ["de"])
            i18n.set_preference("es_419")
            self.assertEqual(i18n.wanted_languages(), ["es_419", "es"])
            i18n.set_preference("en")
            self.assertEqual(i18n.wanted_languages(), [])
            i18n.set_preference("keyboard")
            self.assertEqual(i18n.wanted_languages(), ["de"])

    def test_a_program_started_now_matches_the_open_window(self):
        """Arrow Pad started with an old FRAME_TWEAKS_LANG_RESOLVED while the window shows English:
        English. Once the window has closed (withdraw), the parent's and the keyboard's count again."""
        with mock.patch.object(i18n, "keyboard_language", lambda: "de"), mock.patch.object(i18n, "INHERIT", True), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANG_RESOLVED": "es_419"}, clear=True):
            i18n._write(i18n.ANNOUNCED, "en\n")
            self.assertEqual(i18n.wanted_languages(), [])
            i18n.withdraw()
            self.assertEqual(i18n.wanted_languages(), ["es_419", "es"])

    def test_a_window_that_died_isnt_followed(self):
        """A window ended without withdrawing (a SteamVR restart, a kill): every program followed
        its language until the Frame restarted."""
        gone = subprocess.Popen(["true"])
        gone.wait()
        i18n._write(i18n.ANNOUNCED, f"es_419\n{gone.pid}\n")
        self.assertIsNone(i18n.announced())
        i18n._write(i18n.ANNOUNCED, f"es_419\n{os.getpid()}\n")
        self.assertEqual(i18n.announced(), "es_419")
        i18n._write(i18n.ANNOUNCED, "en\n")                      # (one written before: as it says)
        self.assertEqual(i18n.announced(), "en")

    def test_programs_follow_the_window(self):
        """The window announces; a Qt program watching switches (inotify, no polling)."""
        from PyQt6.QtCore import QCoreApplication, QObject
        app = QCoreApplication.instance() or QCoreApplication([])
        (self.d / "es_419.po").write_text('msgid ""\nmsgstr ""\n\nmsgid "Close"\nmsgstr "Cerrar"\n')
        heard = []
        owner = QObject()
        with mock.patch.object(i18n, "LOCALE", self.d), mock.patch.object(i18n, "CATALOGUE", i18n.Catalogue([])), \
                mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FRAME_TWEAKS_DRY_RUN", None)
            i18n.follow_announcements(owner, lambda: heard.append(i18n._("Close")))
            i18n.announce("es_419")
            for _n in range(50):
                app.processEvents()
                if heard:
                    break
                import time
                time.sleep(0.02)
            self.assertEqual(heard, ["Cerrar"])


class Keyboard(unittest.TestCase):
    """The active keyboard's language: Steam's VR keyboard (VR session) or KDE's layout (desktop),
    looked at no more than once every 5 s."""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.d)])
        for name, value in (("STEAM_CONFIG", self.d / "config.vdf"), ("STEAM_USERS", str(self.d / "u*/localconfig.vdf"))):
            p = mock.patch.object(i18n, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.dict(i18n._keyboard, {"at": None, "value": None, "files": {}})
        p.start()
        self.addCleanup(p.stop)

    def steam(self, layout, f="config.vdf"):
        (self.d / f).parent.mkdir(parents=True, exist_ok=True)
        (self.d / f).write_text('"InstallConfigStore"\n{\n\t\t"keyboard_layout"\t\t'
                                f'"{{\\"currentLayout\\":{layout},\\"selectedLayouts\\":[0,19]}}"\n}}\n')

    def test_steam_keyboard_in_vr(self):
        with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True):
            self.steam(19)
            self.assertEqual(i18n.keyboard_language(), "es")
            self.assertEqual(i18n.wanted_languages(), ["es"])
            self.steam(0)                                       # QWERTY: says nothing
            self.assertEqual(i18n.keyboard_language(), "es")    # (not looked at again yet)
            i18n._keyboard["at"] -= i18n.CHECK_EVERY
            self.assertIsNone(i18n.keyboard_language())

    def test_newest_steam_file_wins(self):
        with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True):
            self.steam(0)
            self.steam(8, "u1/localconfig.vdf")
            os.utime(self.d / "config.vdf", (1, 1))
            self.assertEqual(i18n.keyboard_language(), "de")

    def test_kde_layout_in_desktop_mode(self):
        (self.d / "kxkbrc").write_text("[Layout]\nLayoutList=latam\nUse=true\n")
        with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE", "XDG_CONFIG_HOME": str(self.d),
                                          "LANG": "en_US.UTF-8"}, clear=True):
            self.assertEqual(i18n.keyboard_language(), "es_419")
            self.assertEqual(i18n.wanted_languages(), ["es_419", "es", "en_US", "en"])

    def test_kde_keyboard_as_kwin_reads_it(self):
        """The layout and its variant (lib/xkb.py types on them), KWin's model default and the
        options only with ResetOldOptions; the active one of several, as KDE says (qdbus6)."""
        def keyboard(text, active="1"):
            (self.d / "kxkbrc").write_text(text)
            answer = subprocess.CompletedProcess([], 0, stdout=active + "\n")
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.d)}), \
                    mock.patch.object(i18n.subprocess, "run", return_value=answer):
                return i18n.kde_keyboard()
        self.assertEqual(keyboard("[Layout]\nLayoutList=fr\nVariantList=oss\nUse=true\n"),
                         {"layout": "fr", "variant": "oss", "model": "pc104", "options": ""})
        self.assertEqual(keyboard("[Layout]\nLayoutList=us,de\nVariantList=,nodeadkeys\nModel=pc105\n"
                                  "Options=lv3:ralt_switch\nResetOldOptions=true\n"),
                         {"layout": "de", "variant": "nodeadkeys", "model": "pc105", "options": "lv3:ralt_switch"})
        self.assertEqual(keyboard("[Layout]\nLayoutList=us,de(nodeadkeys)\nOptions=caps:none\n")["variant"],
                         "nodeadkeys")                         # (older KDE: the variant in brackets)
        self.assertEqual(keyboard("[Layout]\nLayoutList=us,de\n", active="nonsense")["layout"], "us")
        self.assertIsNone(keyboard("[Layout]\nUse=true\n"))
        (self.d / "kxkbrc").unlink()
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.d)}):
            self.assertIsNone(i18n.kde_keyboard())

    def test_off(self):
        self.steam(19)
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_KEYBOARD": "0"}, clear=True):
            self.assertIsNone(i18n.keyboard_language())

    def test_same_language_elsewhere(self):
        """es and es_MX use es_419.po (the only Spanish one)."""
        (self.d / "es_419.po").write_text('msgid ""\nmsgstr ""\n\nmsgid "Close"\nmsgstr "Cerrar"\n')
        self.assertEqual(i18n.pick(["es"], self.d).name, "es_419.po")
        self.assertEqual(i18n.Catalogue(["es_MX"], self.d).gettext("Close"), "Cerrar")
        self.assertIsNone(i18n.pick(["de", "fr"], self.d))

    def test_the_languages_own_file_before_another_regions(self):
        """Once there's an es.po, Spanish from Spain or Mexico uses it (locale/README.md); pt_PT
        takes pt.po, not pt_BR.po."""
        for f in ("es_419.po", "es.po", "pt_BR.po", "pt.po"):
            (self.d / f).write_text('msgid ""\nmsgstr ""\n')
        for languages, file in ((["es_ES", "es"], "es.po"), (["es_MX", "es"], "es.po"), (["es_419", "es"], "es_419.po"),
                                (["pt_PT", "pt"], "pt.po"), (["pt_BR", "pt"], "pt_BR.po")):
            self.assertEqual(i18n.pick(languages, self.d).name, file, languages)


class Shell(unittest.TestCase):
    def test_t(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(d)])
        (d / "locale").mkdir()
        for f in ("i18n.py", "i18n.sh"):
            (d / f).write_text((ROOT / "lib" / f).read_text())
        (d / "locale/es_419.po").write_text('msgid ""\nmsgstr ""\n\nmsgid "Fetching %s"\nmsgstr "Descargando %s"\n\n'
                                           'msgid "Can\'t"\nmsgstr "No se puede"\n')
        script = (f'source {d}/i18n.sh; t "Fetching %s" "a \'b\'"; echo; t "Can\'t"; echo; t "Other 100%"; echo; '
                  'echo "$FRAME_TWEAKS_LANG_RESOLVED"')
        env = {"PATH": os.environ["PATH"], "HOME": str(d), "FRAME_TWEAKS_LANGUAGE": "es", "FRAME_TWEAKS_KEYBOARD": "0"}
        out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True).stdout
        self.assertEqual(out.splitlines(), ["Descargando a 'b'", "No se puede", "Other 100%", "es_419"])
        env["FRAME_TWEAKS_LANG_RESOLVED"] = "en"                # (a script started by one that found none)
        out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True).stdout
        self.assertEqual(out.splitlines()[0], "Fetching a 'b'")


class MenusAndDashboard(unittest.TestCase):
    """Menu entries get Name[lang]= lines at install; the dashboard patches get their text from
    sft-dashboard (window.__sftI18n), for T(...) / N(...) in their JS."""
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.d)])
        (self.d / "es_419.po").write_text('msgid ""\nmsgstr ""\n\nmsgid "Lock Wallet"\nmsgstr "Bloquear cartera"\n\n'
                                          'msgid "Colour"\nmsgstr "Color"\n\nmsgid "Off"\nmsgstr "Desactivado"\n')

    def test_desktop(self):
        en = i18n.Catalogue([], self.d)
        out = i18n.desktop("[Desktop Entry]\nName=Lock Wallet\nComment=Untranslated\nExec=x\n", self.d, en)
        self.assertEqual(out.splitlines(), ["[Desktop Entry]", "Name=Lock Wallet", "X-Frame-Tweaks-Name=Lock Wallet",
                                            "Name[es_419]=Bloquear cartera", "Name[es]=Bloquear cartera",
                                            "Comment=Untranslated", "X-Frame-Tweaks-Comment=Untranslated", "Exec=x"])
        es = i18n.Catalogue(["es"], self.d)
        self.assertIn("Name=Bloquear cartera", i18n.desktop("Name=Lock Wallet\n", self.d, es).splitlines())
        again = i18n.desktop(out, self.d, es)                     # (installed again: no duplicates)
        self.assertEqual(again.count("Name[es]="), 1)
        self.assertIn("Name=Bloquear cartera", again.splitlines())

    def test_relabel_when_the_language_changes(self):
        """Only Frame Tweaks' entries, every group (actions too), the English kept."""
        apps = self.d / "apps"
        apps.mkdir()
        en = i18n.Catalogue([], self.d)
        mine = apps / "wallet-lock.desktop"
        mine.write_text(i18n.desktop("[Desktop Entry]\nName=Lock Wallet\n\n[Desktop Action x]\nName=Off\n", self.d, en))
        other = apps / "other.desktop"
        other.write_text("[Desktop Entry]\nName=Lock Wallet\n")
        es = i18n.Catalogue(["es"], self.d)
        with mock.patch.object(i18n, "CATALOGUE", es), mock.patch.object(i18n, "APPS", apps):
            self.assertEqual(i18n.menus((apps,)), [mine])
            self.assertEqual(i18n.menus((apps,)), [])             # (nothing changed: not written)
        lines = mine.read_text().splitlines()
        self.assertIn("Name=Bloquear cartera", lines)
        self.assertIn("Name=Desactivado", lines)
        self.assertIn("X-Frame-Tweaks-Name=Lock Wallet", lines)
        self.assertEqual(other.read_text(), "[Desktop Entry]\nName=Lock Wallet\n")
        with mock.patch.object(i18n, "CATALOGUE", en):
            self.assertTrue(i18n.relabel(mine))
        self.assertIn("Name=Lock Wallet", mine.read_text().splitlines())

    def test_relabel_leaves_a_name_you_gave_it(self):
        """A name of your own (KDE's menu editor writes Name=) isn't one of ours to translate."""
        en, es = i18n.Catalogue([], self.d), i18n.Catalogue(["es"], self.d)
        mine = self.d / "wallet-lock.desktop"
        text = i18n.desktop("[Desktop Entry]\nName=Lock Wallet\n\n[Desktop Action x]\nName=Off\n", self.d, en)
        mine.write_text(text.replace("Name=Lock Wallet\nX-Frame", "Name=Lock it all\nX-Frame", 1))
        with mock.patch.object(i18n, "CATALOGUE", es):
            self.assertTrue(i18n.relabel(mine))                    # (its action's name: ours)
        lines = mine.read_text().splitlines()
        self.assertIn("Name=Lock it all", lines)
        self.assertIn("Name=Desactivado", lines)

    def test_dashboard_table(self):
        sd = load_script(ROOT / "packs/core/vr-dashboard/sft-dashboard", "sd")
        js = self.d / "p.js"
        js.write_text("const T = (s) => s, N = (s) => s;\nconst O = [[N('Off'), 'off']];\nel('div', {}, T('Colour'), 'Other');\n")
        cat = i18n.Catalogue(["es"], self.d)
        with mock.patch.object(sd, "i18n", mock.Mock(CATALOGUE=cat, refresh=lambda: False)), \
                mock.patch.object(sd, "_", cat.gettext):
            expr = sd.i18n_expr({"p": js})
        table = json.loads(expr.split(" = ", 1)[1].rsplit(";", 1)[0])
        self.assertEqual(table, {"lang": "es_419", "t": {"Off": "Desactivado", "Colour": "Color"}})

    def test_patch_text_in_template(self):
        pot = (ROOT / "locale/frame-tweaks.pot").read_text()
        self.assertIn('msgid "Vertical strip"', pot)                # scroll-strips' VR panel
        self.assertIn('msgid "Restart stream"', pot)                # Android Mirror's VR panel
        self.assertIn('msgid "Lock Wallet"', pot)                   # a menu entry


class Template(unittest.TestCase):
    def test_up_to_date_and_complete(self):
        r = subprocess.run([sys.executable, str(ROOT / "dev/i18n.py"), "check"], capture_output=True, text=True)
        if r.returncode and os.environ.get("FRAME_TWEAKS_I18N_LENIENT"):     # (CI, on a pull request)
            self.skipTest("the translation template is out of date: a maintainer refreshes it before merging")
        self.assertEqual(r.returncode, 0, r.stderr)
        pot = (ROOT / "locale/frame-tweaks.pot").read_text()
        self.assertIn('msgid "Refresh"', pot)                               # marked in the code
        self.assertIn('msgid "Arrow Pad"', pot)                             # a tweak's title
        self.assertIn('msgid "VR environment"', pot)                        # a category
        self.assertNotIn('msgid "1.5"', pot)                                # nothing to translate

    def test_manifest_text_is_translated_on_load(self):
        """A tweak's title comes out translated (sft.load), its id and files unchanged."""
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "de.po").write_text('msgid ""\nmsgstr ""\n\nmsgid "Arrow Pad"\nmsgstr "Pfeiltasten"\n', encoding="utf-8")
        import sft
        with mock.patch.object(i18n, "CATALOGUE", i18n.Catalogue(["de"], d)):
            c = next(c for c in sft.load(refresh=True)["components"] if c["id"] == "arrowpad")
            self.assertEqual(c["title"], "Pfeiltasten")
        sft.load(refresh=True)

if __name__ == "__main__":
    unittest.main()
