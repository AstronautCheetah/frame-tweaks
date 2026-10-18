"""dev/fetch-upstream-readmes.py fetches an upstream README's pictures only over https:// from
GitHub (redirects too): a picture at a file: address (a file of yours, gh's token say) or on
another host stays a link, and nothing is read. Offline: the fetching is a stand-in."""
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
fetch = load_script(ROOT / "dev/fetch-upstream-readmes.py", "fetch_upstream_readmes")
RAW = "https://raw.githubusercontent.com/someone/project/v1.0/README.md"


class UpstreamPictures(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.out = self.tmp / "upstream"
        self.out.mkdir()
        self.secret = self.tmp / "hosts.yml"
        self.secret.write_text("oauth_token: " + "x" * 8 + "\n")       # (a stand-in for gh's file)
        self.fetched = []

    def offline(self):
        """The fetching: a stand-in that records what's asked for and answers a picture."""
        def opened(req, timeout=None):
            self.fetched.append(req.full_url)
            return mock.MagicMock(**{"__enter__.return_value.read.return_value": b"PNG"})
        p = mock.patch.object(fetch.OPENER, "open", side_effect=opened)
        p.start()
        self.addCleanup(p.stop)

    def convert(self, text):
        with mock.patch("sys.stderr"):
            return fetch.convert(text, RAW, self.out)

    def test_a_local_file_isnt_read(self):
        """(Only file: pictures here: nothing goes to the network, whatever the version.)"""
        md = self.convert(f'<img src="file://{self.secret}" alt="logo">\n![shot](file://{self.secret})\n'
                          f'![shot](FILE://{self.secret})\n')
        self.assertEqual(list(self.out.iterdir()), [])
        self.assertEqual(md.count(f"](file://{self.secret})"), 2)          # (left as the links they were)
        self.assertIn(f"](FILE://{self.secret})", md)
        self.assertNotIn("upstream/", md)

    def test_only_https_from_github_is_fetched(self):
        self.offline()
        md = self.convert("![a](docs/a.png)\n![b](https://user-images.githubusercontent.com/1/b.png)\n"
                          "![c](http://raw.githubusercontent.com/someone/project/v1.0/c.png)\n"
                          "![d](https://example.com/d.png)\n![e](//example.com/e.png)\n"
                          "![f](https://github.com.example.com/f.png)\n![g](https://user@github.com/g.png)\n"
                          "![h](data:image/png;base64,iVBORw0KGgo=)\n")
        self.assertEqual(self.fetched, ["https://raw.githubusercontent.com/someone/project/v1.0/docs/a.png",
                                        "https://user-images.githubusercontent.com/1/b.png"])
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["a.png", "b.png"])
        self.assertIn("![a](upstream/a.png)", md)
        for kept in ("http://raw.githubusercontent.com/someone/project/v1.0/c.png", "https://example.com/d.png",
                     "https://example.com/e.png", "https://github.com.example.com/f.png",
                     "https://user@github.com/g.png", "data:image/png;base64,iVBORw0KGgo="):
            self.assertIn(f"]({kept})", md)

    def test_a_redirect_away_from_github_is_refused(self):
        redirect = fetch.GitHubOnly()
        req = urllib.request.Request("https://github.com/user-attachments/assets/1")
        ok = redirect.redirect_request(req, None, 302, "Found", {}, "https://private-user-images.githubusercontent.com/1.png")
        self.assertEqual(ok.full_url, "https://private-user-images.githubusercontent.com/1.png")
        for away in ("https://example.com/1.png", f"file://{self.secret}", "http://github.com/1.png"):
            with self.assertRaises(urllib.error.HTTPError):
                redirect.redirect_request(req, None, 302, "Found", {}, away)

    def test_its_opener_reads_no_local_files(self):
        for url in (f"file://{self.secret}", "ftp://example.com/x", "data:,secret"):     # (the real opener)
            with self.assertRaises(urllib.error.URLError, msg=url):
                fetch.OPENER.open(url)
            with self.assertRaises(OSError, msg=url):
                fetch.get(url)


if __name__ == "__main__":
    unittest.main()
