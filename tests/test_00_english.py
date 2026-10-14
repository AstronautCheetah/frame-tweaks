"""Imported first by `python3 -m unittest discover -s tests` (the names sort): the tests check
English text, so they run in English whatever this machine's keyboard or session language is
(lib/i18n.py). Their subprocesses inherit it."""
import os
import tempfile
import unittest

os.environ["FRAME_TWEAKS_LANGUAGE"] = "en"
os.environ["FRAME_TWEAKS_KEYBOARD"] = "0"
# (the window announces its language to running programs: not to the real ones from a test)
# (in folders removed when the tests end)
_ANNOUNCED, _PREFERRED = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
os.environ["FRAME_TWEAKS_ANNOUNCE_FILE"] = os.path.join(_ANNOUNCED.name, "language")
os.environ["FRAME_TWEAKS_PREFERENCE_FILE"] = os.path.join(_PREFERRED.name, "language")   # (⚙ Preferences)


class English(unittest.TestCase):
    def test_tests_run_in_english(self):
        self.assertEqual(os.environ["FRAME_TWEAKS_LANGUAGE"], "en")
