"""Imported first by `python3 -m unittest discover -s tests` (the names sort): the tests check
English text, so they run in English whatever this machine's keyboard or session language is
(lib/i18n.py). Their subprocesses inherit it."""
import os
import unittest

os.environ["FRAME_TWEAKS_LANGUAGE"] = "en"
os.environ["FRAME_TWEAKS_KEYBOARD"] = "0"


class English(unittest.TestCase):
    def test_tests_run_in_english(self):
        self.assertEqual(os.environ["FRAME_TWEAKS_LANGUAGE"], "en")
