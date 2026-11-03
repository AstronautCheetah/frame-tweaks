"""A linked project's update check (its manifest's link.version, lib/link.sh update-check): the
installed version its command prints against where GitHub's latest-release link leads (a stand-in
curl), as "<installed> <newest>" for the window's update hint, or nothing; with a tested version
(lib/tested-versions' link-<id>), "<installed> <newest> <tested>", and what the row then offers
(gui/window_logic.py link_offer): a newer release as not yet tested, the way up or back to the
tested one. In a throwaway home."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "gui"))
import sft  # noqa: E402
import window_logic  # noqa: E402

TESTED = sft.tested_versions()


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
        git = bin_ / "git"                              # (ls-remote: a project without releases' newest commit)
        git.write_text('#!/bin/sh\necho "git $*" >> "$ASKED"\n[ -n "$HEAD_COMMIT" ] || exit 128\n'
                       'printf \'%s\\tHEAD\\n\' "$HEAD_COMMIT"\n')
        git.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=f"{bin_}:{os.environ['PATH']}", ASKED=str(self.asked))

    def check(self, tid, headers=moved_to("v1.4.0"), head=""):  # noqa: B008  (a constant, made once: the usual reply)
        r = subprocess.run(["bash", str(ROOT / "lib/link.sh"), "update-check", tid], capture_output=True, text=True,
                           env=dict(self.env, HEADERS=headers or "", HEAD_COMMIT=head))
        return r.stdout

    def recline(self, version):
        (self.home / ".local/share/recline-vr").mkdir(parents=True, exist_ok=True)
        (self.home / ".local/share/recline-vr/VERSION").write_text(version + "\n")

    def test_recline(self):
        tested = TESTED["link-recline"]
        self.assertEqual(self.check("recline"), "")                 # (not installed: curl not even asked)
        self.assertFalse(self.asked.exists())
        for version, want in (("v1.3.0", f"1.3.0 1.4.0 {tested}\n"),
                              ("v1.4.0", f"1.4.0 1.4.0 {tested}\n"),
                              ("v1.4.0-dirty", f"1.4.0 1.4.0 {tested}\n"),      # (a change of yours: still 1.4.0)
                              ("v1.3.0+3.14d0169-dirty", f"1.3.0+3.14d0169 1.4.0 {tested}\n"),
                              ("unknown+14d0169", "")):                       # (built without its tags)
            with self.subTest(version=version):
                self.recline(version)
                self.assertEqual(self.check("recline"), want)
        self.assertIn("https://github.com/new-waifu/Recline-VR/releases/latest", self.asked.read_text())

    def test_full_keyboard(self):
        """Its installer names a release's folder <version>-install-<random> (0.14.1); before, <version>."""
        releases = self.home / ".local/share/framekeyboard/releases"
        tested = TESTED["link-full-keyboard"]
        for folder in ("0.5.0", "0.5.0-install-Ab12Cd"):
            with self.subTest(folder=folder):
                (releases / folder).mkdir(parents=True, exist_ok=True)
                (releases.parent / "current").unlink(missing_ok=True)
                (releases.parent / "current").symlink_to(f"releases/{folder}")
                self.assertEqual(self.check("full-keyboard", moved_to("0.6.0")), f"0.5.0 0.6.0 {tested}\n")
        self.assertIn("https://github.com/TaiKeid/steam-frame-full-keyboard/releases/latest", self.asked.read_text())

    def test_cuff_a_commit(self):
        """Cuff has no releases: its tested version is a commit, and its newest its default branch's head."""
        (self.home / ".local/share/cuff").mkdir(parents=True)
        (self.home / ".local/share/cuff/frame-tweaks-commit").write_text("bea0789\n")
        self.assertEqual(self.check("cuff", head="0123456789abcdef0123456789abcdef01234567"),
                         f"bea0789 0123456 {TESTED['link-cuff'][:7]}\n")
        self.assertIn("git ls-remote https://github.com/Brobert-in-aus/cuff HEAD", self.asked.read_text())
        self.assertEqual(self.check("cuff"), "bea0789 - bea0789\n")          # (offline)

    def test_offline_or_no_release(self):
        """Nothing newer to say, but the tested version still is (the way back to it)."""
        self.recline("v1.3.0")
        tested = TESTED["link-recline"]
        self.assertEqual(self.check("recline", headers=None), f"1.3.0 - {tested}\n")
        self.assertEqual(self.check("recline", headers="HTTP/2 404\r\n\r\n"), f"1.3.0 - {tested}\n")

    def test_the_window_finds_it(self):
        """sft.script: a link's update check is lib/link.sh's, only with link.version."""
        comps = {c["id"]: c for c in sft.load(refresh=True)["components"]}
        self.assertEqual(sft.script(comps["recline"], "update-check")[1:],
                         [str(sft.LINK_HELPER), "update-check", "recline"])
        self.assertEqual(comps["recline"]["link"]["github"], "new-waifu/Recline-VR")
        no_version = dict(comps["recline"], link={k: v for k, v in comps["recline"]["link"].items() if k != "version"})
        self.assertIsNone(sft.script(no_version, "update-check"))

    def test_every_official_link_installs_its_tested_version(self):
        """Each official link reads $FT_LINK_VERSION, and lib/tested-versions has its link-<id>: a
        release tag, or for a project without releases a whole commit (its archive by commit)."""
        links = [c for c in sft.load(refresh=True)["components"] if c["link"] and c["official"]]
        self.assertLessEqual({"recline", "full-keyboard", "perf-overlay", "knockthru", "cuff"}, {c["id"] for c in links})
        for c in links:
            with self.subTest(c["id"]):
                self.assertRegex(c["link"]["install"], r"\$\{?FT_LINK_VERSION\b")
                self.assertEqual(c["link"]["tested"], TESTED[f"link-{c['id']}"])
        self.assertRegex(TESTED["link-cuff"], r"^[0-9a-f]{40}$")

    def test_github_repo(self):
        self.assertEqual(sft.github_repo(None, "https://github.com/a/b#readme"), "a/b")
        self.assertEqual(sft.github_repo("https://github.com/a/b.git"), "a/b")
        self.assertIsNone(sft.github_repo("https://example.org/a/b", None))


class LinkOffer(unittest.TestCase):
    """What a linked project's row offers (window_logic.link_offer), from "<installed> <newest>
    <tested>" and which one Frame Tweaks installed."""
    offer = staticmethod(window_logic.link_offer)

    def test_the_tested_version_installed(self):
        self.assertIsNone(self.offer("1.4.0", "1.4.0", "v1.4.0", "tested"))     # (nothing newer)
        self.assertIsNone(self.offer("1.4.0", "-", "v1.4.0", "tested"))         # (offline)

    def test_a_newer_release_is_offered_as_untested(self):
        self.assertEqual(self.offer("1.4.0", "1.5.0", "v1.4.0", "tested"),
                         {"tested": "v1.4.0", "newest": "1.5.0", "to_tested": None})

    def test_after_the_newest_the_way_back(self):
        self.assertEqual(self.offer("1.5.0", "1.5.0", "v1.4.0", "newest"),
                         {"tested": "v1.4.0", "newest": None, "to_tested": "back"})
        self.assertEqual(self.offer("1.5.0", "1.6.0", "v1.4.0", "newest"),            # (and a newer one still)
                         {"tested": "v1.4.0", "newest": "1.6.0", "to_tested": "back"})
        self.assertEqual(self.offer("1.5.0", "-", "v1.4.0", None)["to_tested"], "back")   # (its own updater)

    def test_older_than_the_tested_one_goes_up(self):
        """Installed before Frame Tweaks tested a newer one (an update not run yet, or an install
        from before tested versions): Update to the tested one."""
        self.assertEqual(self.offer("1.3.0", "1.4.0", "v1.4.0", "tested"),
                         {"tested": "v1.4.0", "newest": None, "to_tested": "up"})
        self.assertEqual(self.offer("1.3.0", "1.5.0", "v1.4.0", None),
                         {"tested": "v1.4.0", "newest": "1.5.0", "to_tested": "up"})

    def test_a_commit(self):
        """No releases: any other commit is newer; back or up by which was asked for."""
        self.assertIsNone(self.offer("bea0789", "bea0789", "bea0789"[:7], "tested"))
        self.assertEqual(self.offer("bea0789", "0123456", "bea0789", "tested"),
                         {"tested": "bea0789", "newest": "0123456", "to_tested": None})
        self.assertEqual(self.offer("0123456", "0123456", "bea0789", "newest"),
                         {"tested": "bea0789", "newest": None, "to_tested": "back"})
        self.assertEqual(self.offer("0123456", "-", "bea0789", "tested")["to_tested"], "up")

    def test_same_version(self):
        same = window_logic.same_version
        self.assertTrue(same("v1.4.0", "1.4.0"))
        self.assertTrue(same("bea0789", "bea0789859d3d6ae3d1972dc91189544e7f831b9"))
        self.assertFalse(same("1.4.0", "1.4.1"))
        self.assertFalse(same("bea0789", "bea0780"))
        self.assertFalse(same("1.4.0", None))

    def test_the_window_reads_it(self):
        """update_check: three words from a link with a tested version are link_offer's."""
        c = dict(sft.component("recline"))
        with mock.patch.object(window_logic, "component", return_value=c), \
                mock.patch.object(window_logic.subprocess, "run",
                                  return_value=subprocess.CompletedProcess([], 0, "1.4.0 1.5.0 v1.4.0\n", "")), \
                mock.patch.object(window_logic.sft, "link_choice", return_value=("tested", "v1.4.0")):
            self.assertEqual(window_logic.update_check("recline"),
                             {"tested": "v1.4.0", "newest": "1.5.0", "to_tested": None})


if __name__ == "__main__":
    unittest.main()
