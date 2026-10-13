"""Shell helpers in lib/common.sh. Run: python3 -m unittest -v"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(script, stdin="", **env):
    with tempfile.TemporaryDirectory() as home:      # common.sh creates folders in $HOME
        return subprocess.run(["bash", "-c", f"source {ROOT}/lib/common.sh 2>/dev/null; {script}"],
                              input=stdin, capture_output=True, text=True,
                              env={**os.environ, "HOME": home, **env}).stdout.strip()


class NewestTag(unittest.TestCase):
    TAGS = "v0.9.0\nv0.10.0\nv0.10.1-rc1\nv0.10.1-rc2\nfoo\n"

    def test_stable(self):
        self.assertEqual(sh("newest_tag", self.TAGS, FRAME_TWEAKS_CHANNEL="stable"), "v0.10.0")

    def test_beta_takes_latest_prerelease(self):
        self.assertEqual(sh("newest_tag", self.TAGS, FRAME_TWEAKS_CHANNEL="beta"), "v0.10.1-rc2")

    def test_beta_final_beats_its_prerelease(self):
        self.assertEqual(sh("newest_tag", "v1.0.0-rc1\nv1.0.0\n", FRAME_TWEAKS_CHANNEL="beta"), "v1.0.0")


class Pins(unittest.TestCase):
    def test_every_pin_is_complete(self):
        for pin in ROOT.glob("*/pin"):
            fields = dict(l.split("=", 1) for l in pin.read_text().splitlines() if "=" in l and not l.startswith("#"))
            self.assertTrue(fields.get("url", "").startswith("https://"), pin)
            if "rev" in fields:                       # a git commit
                self.assertRegex(fields["rev"], r"^[0-9a-f]{40}$", pin)
            else:                                     # a file, at a versioned URL
                self.assertRegex(fields.get("sha256", ""), r"^[0-9a-f]{64}$", pin)
                self.assertIn(fields.get("version", "?"), fields["url"], pin)

    def test_python_constraints_are_exact(self):
        for line in (ROOT / "lib" / "python-constraints.txt").read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                self.assertRegex(line, r"^[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*$")


if __name__ == "__main__":
    unittest.main()
