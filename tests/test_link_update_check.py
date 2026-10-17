"""A linked project's update check (its manifest's link.version, lib/link.sh update-check): the
installed version its command prints against where GitHub's latest-release link leads (a stand-in
curl), as "<installed> <newest>" for the window's update hint, or nothing. In a throwaway home."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "lib"))
import sft  # noqa: E402


def moved_to(tag):
    return f"HTTP/2 302\r\nlocation: https://github.com/someone/project/releases/tag/{tag}\r\n\r\n"


class LinkUpdateCheck(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home, bin_ = Path(tmp.name, "home"), Path(tmp.name, "bin")
        self.home.mkdir()
        bin_.mkdir()
        self.asked = Path(tmp.name, "asked")
        curl = bin_ / "curl"
        curl.write_text('#!/bin/sh\necho "$@" >> "$ASKED"\n[ -n "$HEADERS" ] || exit 6\nprintf \'%s\' "$HEADERS"\n')
        curl.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=f"{bin_}:{os.environ['PATH']}", ASKED=str(self.asked))

    def check(self, tid, headers=moved_to("v1.4.0")):
        r = subprocess.run(["bash", str(ROOT / "lib/link.sh"), "update-check", tid], capture_output=True, text=True,
                           env=dict(self.env, HEADERS=headers or ""))
        return r.stdout

    def recline(self, version):
        (self.home / ".local/share/recline-vr").mkdir(parents=True, exist_ok=True)
        (self.home / ".local/share/recline-vr/VERSION").write_text(version + "\n")

    def test_recline(self):
        self.assertEqual(self.check("recline"), "")                 # (not installed: curl not even asked)
        self.assertFalse(self.asked.exists())
        for version, want in (("v1.3.0", "1.3.0 1.4.0\n"),
                              ("v1.4.0", "1.4.0 1.4.0\n"),
                              ("v1.4.0-dirty", "1.4.0 1.4.0\n"),      # (a change of yours: still 1.4.0)
                              ("v1.3.0+3.14d0169-dirty", "1.3.0+3.14d0169 1.4.0\n"),
                              ("unknown+14d0169", "")):               # (built without its tags)
            with self.subTest(version=version):
                self.recline(version)
                self.assertEqual(self.check("recline"), want)
        self.assertIn("https://github.com/new-waifu/Recline-VR/releases/latest", self.asked.read_text())

    def test_full_keyboard(self):
        releases = self.home / ".local/share/framekeyboard/releases"
        (releases / "0.5.0").mkdir(parents=True)
        (releases.parent / "current").symlink_to("releases/0.5.0")
        self.assertEqual(self.check("full-keyboard", moved_to("0.6.0")), "0.5.0 0.6.0\n")
        self.assertIn("https://github.com/TaiKeid/steam-frame-full-keyboard/releases/latest", self.asked.read_text())

    def test_offline_or_no_release_says_nothing(self):
        self.recline("v1.3.0")
        self.assertEqual(self.check("recline", headers=None), "")
        self.assertEqual(self.check("recline", headers="HTTP/2 404\r\n\r\n"), "")

    def test_the_window_finds_it(self):
        """sft.script: a link's update check is lib/link.sh's, only with link.version."""
        comps = {c["id"]: c for c in sft.load(refresh=True)["components"]}
        self.assertEqual(sft.script(comps["recline"], "update-check")[1:],
                         [str(sft.LINK_HELPER), "update-check", "recline"])
        self.assertEqual(comps["recline"]["link"]["github"], "new-waifu/Recline-VR")
        no_version = dict(comps["recline"], link={k: v for k, v in comps["recline"]["link"].items() if k != "version"})
        self.assertIsNone(sft.script(no_version, "update-check"))

    def test_github_repo(self):
        self.assertEqual(sft.github_repo(None, "https://github.com/a/b#readme"), "a/b")
        self.assertEqual(sft.github_repo("https://github.com/a/b.git"), "a/b")
        self.assertIsNone(sft.github_repo("https://example.org/a/b", None))


if __name__ == "__main__":
    unittest.main()
