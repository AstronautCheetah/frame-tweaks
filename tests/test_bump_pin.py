"""dev/bump-pin.py: a bumped pin's licence texts (license_file=, which dev/mirror-pins.sh copies
beside Frame Tweaks' copy) move to the new version with it; they stayed at the old one. GitHub's
answers and the download are stand-ins."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script  # noqa: E402

bp = load_script(ROOT / "dev/bump-pin.py", "bump_pin")
RELEASE = """version=1.1.2
url=https://github.com/o/app/releases/download/v1.1.2/app-1.1.2-linux-arm64.tar.gz
sha256=aa
latest=https://api.github.com/repos/o/app/releases/latest
license_file=https://raw.githubusercontent.com/o/app/v1.1.2/LICENSE.txt
"""
COMMIT = """version=2026-10-10+7a3f48c
url=https://raw.githubusercontent.com/o/install/7a3f48c7e498d7df3237fd41c30f4d492857edf4/install.sh
rev=7a3f48c7e498d7df3237fd41c30f4d492857edf4
sha256=aa
latest=https://api.github.com/repos/o/install/commits/HEAD
license_file=https://raw.githubusercontent.com/o/install/7a3f48c7e498d7df3237fd41c30f4d492857edf4/LICENSE.txt
"""
NEW_REV = "e5b3c5834e3932c8aaa42deef4794076c9b0cbf0"


def answers(url, binary=False):
    if url.endswith("/releases/latest"):
        return json.dumps({"tag_name": "v1.3.3"})
    return json.dumps({"sha": NEW_REV, "commit": {"committer": {"date": "2026-11-13T00:00:00Z"}}})


class LicenceFollows(unittest.TestCase):
    def bumped(self, text):
        with tempfile.TemporaryDirectory() as d:
            pin = Path(d) / "pin"
            pin.write_text(text)
            old = bp.get, bp.sha256_of, bp.ROOT
            bp.get, bp.sha256_of, bp.ROOT = answers, lambda url: "bb", Path(d)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    bp.bump(pin)
            finally:
                bp.get, bp.sha256_of, bp.ROOT = old
            return bp.read_pin(pin)

    def test_a_release(self):
        p = self.bumped(RELEASE)
        self.assertEqual(p["version"], "1.3.3")
        self.assertEqual(p["license_file"], "https://raw.githubusercontent.com/o/app/v1.3.3/LICENSE.txt")

    def test_a_commit(self):
        p = self.bumped(COMMIT)
        self.assertEqual(p["rev"], NEW_REV)
        self.assertEqual(p["license_file"], f"https://raw.githubusercontent.com/o/install/{NEW_REV}/LICENSE.txt")


if __name__ == "__main__":
    unittest.main()
