"""dev/fresh-install.sh stops before any sandbox when it can't go on, and leaves nothing behind:
not run in desktop mode (no display for the window), or asked for a source it doesn't know (its
throwaway folder, made by then, is removed: the clean-up once stopped on a missing file under
set -e and kept it)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT  # noqa: E402

SCRIPT = ROOT / "dev/fresh-install.sh"


@unittest.skipUnless(shutil.which("bwrap") and shutil.which("pasta"), "needs bwrap and pasta (SteamOS has both)")
class FreshInstall(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cache = Path(tmp.name)

    def run_it(self, *args, display=True):
        env = {"PATH": "/usr/bin:/bin", "HOME": str(self.cache), "XDG_CACHE_HOME": str(self.cache)}
        if display:
            env["DISPLAY"] = ":99"
        return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=30)

    def test_outside_desktop_mode_it_says_so(self):
        r = self.run_it(display=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("desktop mode", r.stderr)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_an_unknown_source_leaves_nothing(self):
        r = self.run_it("--from", "nowhere")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--from", r.stderr)
        self.assertEqual(list((self.cache / "frame-tweaks").iterdir()), [])

    def test_unknown_option(self):
        r = self.run_it("--frobnicate")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown option", r.stderr)


if __name__ == "__main__":
    unittest.main()
