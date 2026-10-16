"""dev/check-links.py: a linked project's release newer than the one last looked at is worth a
look; a README that no longer names what the link's status checks needs attention (Recline-VR
1.3 moved the file it checked). GitHub's answers are stand-ins."""
import json
import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script  # noqa: E402

cl = load_script(ROOT / "dev/check-links.py", "check_links")
RECLINE = ("recline", "Recline", {"installed": "~/.local/share/recline-vr/uninstall.sh"}, "new-waifu/Recline-VR")


def github(release=None, readme="uninstall with ~/.local/share/recline-vr/uninstall.sh"):
    def get(url):
        if url.endswith("/releases/latest"):
            return release and json.dumps({"tag_name": release, "published_at": "2026-10-16T18:20:38Z",
                                           "html_url": f"https://github.com/new-waifu/Recline-VR/releases/{release}"})
        return readme
    return get


class Links(unittest.TestCase):
    def test_a_release_not_looked_at(self):
        red, yellow = cl.check([RECLINE], {"link-recline": "v1.2.0"}, github("v1.3.0"))
        self.assertEqual(red, [])
        self.assertEqual(len(yellow), 1)
        self.assertIn("**v1.3.0** is out (2026-10-16; last looked at: v1.2.0)", yellow[0])
        self.assertIn("`link-recline=v1.3.0`", yellow[0])
        self.assertEqual(cl.check([RECLINE], {"link-recline": "v1.3.0"}, github("v1.3.0")), ([], []))

    def test_a_readme_that_no_longer_names_the_checked_file(self):
        red, _yellow = cl.check([RECLINE], {"link-recline": "v1.3.0"}, github("v1.3.0", readme="run reclinectl"))
        self.assertEqual(len(red), 1)
        self.assertIn("`~/.local/share/recline-vr/uninstall.sh`", red[0])
        red, _yellow = cl.check([RECLINE], {}, github(None, readme="$HOME/.local/share/recline-vr/uninstall.sh"))
        self.assertEqual(red, [])                           # (written with $HOME: named all the same)

    def test_no_releases_off_github_and_unreachable(self):
        self.assertEqual(cl.check([RECLINE], {}, github(None)), ([], []))
        _red, yellow = cl.check([("x", "X", {"installed": "~/x"}, None)], {}, github())
        self.assertIn("isn't on GitHub", yellow[0])

        def down(url):
            raise urllib.error.URLError("no network")
        _red, yellow = cl.check([RECLINE], {}, down)
        self.assertIn("couldn't reach", yellow[0])

    def test_the_official_links_are_found(self):
        found = {tid: repo for tid, _title, _link, repo in cl.links()}
        self.assertEqual(found.get("recline"), "new-waifu/Recline-VR")
        self.assertEqual(found.get("full-keyboard"), "TaiKeid/steam-frame-full-keyboard")
        for tid in found:
            self.assertIn(f"link-{tid}", cl.tested(), "lib/tested-versions: the release last looked at")


if __name__ == "__main__":
    unittest.main()
