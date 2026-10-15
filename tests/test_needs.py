"""lib/needs.py: a feature that needs a tweak that isn't installed says so in a dialog (seen in
VR, where a notification isn't), offering to open Frame Tweaks on that tweak. And the callers:
Arrow Pad's 🎤 and Snip buttons, Screen snip's Narrate and Copy text."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import needs  # noqa: E402


class Offer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.entry = Path(self.tmp.name) / "ft.desktop"
        p = mock.patch.object(needs, "ENTRY", self.entry)
        p.start()
        self.addCleanup(p.stop)

    def offer(self, *args, **kw):
        run = mock.Mock()
        with mock.patch.object(needs.shutil, "which", lambda n: "/usr/bin/" + n), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANG_RESOLVED": "es_419"}):
            needs.offer(*args, run=run, **kw)
        run.assert_called_once()
        return run.call_args

    def test_asks_then_opens_frame_tweaks_on_that_tweak(self):
        self.entry.write_text("[Desktop Entry]\nName=Frame Tweaks\nExec=env FRAME_TWEAKS_GUI=1 \"/x/frame tweaks/install.sh\" gui\n")
        call = self.offer("dictation", "Dictation isn't installed", "The 🎤 button types what you say.")
        args = call.args[0]
        self.assertEqual(args[:2], ["bash", "-c"])
        self.assertIn("--yesno", args[2])                                  # (asks first)
        self.assertEqual(args[-6:], ["env", "FRAME_TWEAKS_GUI=1", "/x/frame tweaks/install.sh", "gui", "--show", "dictation"])
        self.assertIn("Open Frame Tweaks to install it?", args[7])
        self.assertTrue(call.kwargs["start_new_session"])                  # (doesn't wait for the answer)
        self.assertNotIn("FRAME_TWEAKS_LANG_RESOLVED", call.kwargs["env"])  # (the window picks its own language)

    def test_another_question(self):
        self.entry.write_text("Exec=/x/install.sh gui\n")
        args = self.offer("snip", "Tesseract is missing", "…", question="Reinstall it?").args[0]
        self.assertIn("Reinstall it?", args[7])

    def test_without_frame_tweaks_it_only_says_so(self):
        args = self.offer("speech", "Narrate needs the Speech engine", "…").args[0]   # (no menu entry)
        self.assertEqual(args[:4], ["kdialog", "--title", "Narrate needs the Speech engine", "--sorry"])
        self.assertIn("isn't installed any more", args[4])


class Callers(unittest.TestCase):
    def test_each_feature_offers_its_tweak(self):
        for path, calls in (("packs/original/arrowpad/arrowpad.py", ['needs.offer("snip"', 'needs.offer("dictation"']),
                            ("packs/original/snip/frame-snip", ['needs.offer("speech"', 'needs.offer("snip"'])):
            text = (ROOT / path).read_text()
            for c in calls:
                self.assertIn(c, text, path)
            self.assertNotIn("in Frame Tweaks to use this button", text)      # (the old notification only)

    def test_installed_with_the_shared_modules(self):
        self.assertIn('"$REPO_DIR/lib/needs.py"', (ROOT / "lib/common.sh").read_text())


if __name__ == "__main__":
    unittest.main()
