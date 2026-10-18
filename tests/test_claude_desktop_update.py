"""claude-desktop-update with Anthropic's apt list and packages served by a stand-in curl: it
takes the claude-desktop entry (not another package's) at the newest version, compared as dpkg
compares them (epoch, ~, numbers as numbers), and installs it only if that's newer than the one
installed: an older one (an old copy of the list) only with --allow-older. Both come over HTTPS
only, redirects included, and the file's place in the list must be a plain path. (It took the
list's highest version of any package, installed any version that differed from yours, and
followed a redirect to http://.) In a throwaway home; pgrep, pkill and update-desktop-database
are stand-ins (nothing runs)."""
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
UPDATE = ROOT / "packs/integrations/claude-desktop/claude-desktop-update"
REPO = "https://downloads.claude.ai/claude-desktop/apt/stable"
# curl stand-in: $REPO/<path> is $SERVE/<path> (-o: copied there, else printed); anything else
# fails like a 404. Each URL asked for goes to $CURL_LOG, each call's arguments to $CURL_LOG.args.
CURL = """out=""; url=""; echo "$*" >> "$CURL_LOG.args"
while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift ;; http*) url=$1 ;; esac; shift; done
echo "$url" >> "$CURL_LOG"
case $url in "$REPO"/*) f="$SERVE/${url#"$REPO"/}" ;; *) exit 22 ;; esac
[ -f "$f" ] || exit 22
if [ -n "$out" ]; then cp "$f" "$out"; else cat "$f"; fi"""


def deb(version):
    """A .deb (an ar archive) whose data.tar.xz holds Claude Desktop <version>: the program, an
    icon and its menu entry, where the real package has them."""
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:xz") as tar:
        for name, text, mode in (
                ("usr/lib/claude-desktop/claude-desktop", f"#!/bin/sh\necho {version}\n", 0o755),
                ("usr/share/icons/hicolor/256x256/apps/claude-desktop.png", "png", 0o644),
                ("usr/share/applications/com.anthropic.Claude.desktop",
                 "[Desktop Entry]\nType=Application\nName=Claude\nExec=claude-desktop %u\n", 0o644)):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(text.encode()), mode
            tar.addfile(info, io.BytesIO(text.encode()))
    out = b"!<arch>\n"
    for name, body in (("debian-binary", b"2.0\n"), ("control.tar.xz", b""), ("data.tar.xz", data.getvalue())):
        out += f"{name + '/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(body):<10}`\n".encode() + body
        out += b"\n" if len(body) % 2 else b""
    return out


@unittest.skipUnless(shutil.which("bsdtar") and shutil.which("tar"), "needs bsdtar")
class ClaudeDesktopUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.home, self.serve, self.stubs, self.curl_log = t / "home", t / "serve", t / "stubs", t / "curl.log"
        self.home.mkdir()
        stub(self.stubs, "curl", CURL)
        stub(self.stubs, "pgrep", "exit 1")                  # (Claude isn't running)
        for name in ("pkill", "update-desktop-database"):
            stub(self.stubs, name, "exit 0")
        self.opt = self.home / ".local/opt/claude-desktop"

    def index(self, *entries):
        """Anthropic's list for arm64: (package, version) entries, each with its own .deb; or
        (package, version, path), a place in the list with no file there."""
        stanzas = []
        for package, version, *where in entries:
            path = where[0] if where else f"pool/main/c/{package}/{package}_{version.replace(':', '%3a')}_arm64.deb"
            digest = "0" * 64
            if not where:
                (self.serve / path).parent.mkdir(parents=True, exist_ok=True)
                (self.serve / path).write_bytes(deb(f"{package} {version}"))
                digest = hashlib.sha256((self.serve / path).read_bytes()).hexdigest()
            stanzas.append(f"Package: {package}\nVersion: {version}\nArchitecture: arm64\nFilename: {path}\n"
                           f"Size: 1\nSHA256: {digest}\nDescription: Claude\n A second line\n")
        listing = self.serve / "dists/stable/main/binary-arm64/Packages"
        listing.parent.mkdir(parents=True, exist_ok=True)
        listing.write_text("\n".join(stanzas))

    def installed(self, version):
        self.opt.mkdir(parents=True)
        (self.opt / "claude-desktop").write_text("#!/bin/sh\necho mine\n")
        (self.opt / ".deb-version").write_text(version + "\n")

    def update(self, *args):
        env = sandbox_env(self.home, self.stubs, REPO=REPO, SERVE=self.serve, CURL_LOG=self.curl_log)
        r = subprocess.run(["bash", str(UPDATE), *args], env=env, capture_output=True, text=True, timeout=120)
        self.downloads = [u for u in self.curl_log.read_text().splitlines() if u.endswith(".deb")] \
            if self.curl_log.exists() else []
        return r

    def version(self):
        return (self.opt / ".deb-version").read_text().strip()

    def test_takes_claude_desktops_own_entry_at_its_newest(self):
        self.index(("claude-desktop", "2.9.0"), ("claude-desktop-beta", "9.0.0"), ("claude-desktop", "2.10.0"),
                   ("claude-desktop", "2.10.0~rc1"))
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.version(), "2.10.0")
        self.assertIn("echo claude-desktop 2.10.0", (self.opt / "claude-desktop").read_text())
        self.assertEqual(self.downloads, [f"{REPO}/pool/main/c/claude-desktop/claude-desktop_2.10.0_arm64.deb"])

    def test_dpkgs_order(self):
        """An epoch outranks the rest; numbers count as numbers, and a ~ pre-release of 3.0.0 is
        newer than 2.99.0 (and older than 3.0.0 itself: the test above has 2.10.0~rc1)."""
        self.index(("claude-desktop", "3.0.0~beta1"), ("claude-desktop", "1:0.1"), ("claude-desktop", "2.99.0"))
        self.assertEqual(self.update().returncode, 0)
        self.assertEqual(self.version(), "1:0.1")
        shutil.rmtree(self.opt)
        self.index(("claude-desktop", "3.0.0~beta1"), ("claude-desktop", "2.99.0"))
        self.assertEqual(self.update().returncode, 0)
        self.assertEqual(self.version(), "3.0.0~beta1")

    def test_a_newer_one_replaces_yours(self):
        self.installed("2.9.0")
        self.index(("claude-desktop", "2.10.0"))
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Claude Desktop: 2.9.0 -> 2.10.0", r.stdout)
        self.assertEqual(self.version(), "2.10.0")

    def test_the_same_one_does_nothing(self):
        self.installed("2.10.0")
        self.index(("claude-desktop", "2.10.0"))
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Claude Desktop already at 2.10.0", r.stdout)
        self.assertEqual(self.downloads, [])

    def test_an_older_one_only_when_asked(self):
        """An old copy of the list, served again (it isn't signed), can't take you back."""
        self.installed("2.11.0")
        self.index(("claude-desktop", "2.10.0"), ("claude-desktop", "2.9.0"))
        r = self.update()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Claude Desktop 2.11.0 is newer than the 2.10.0 in Anthropic's list, so it stays.", r.stdout)
        self.assertIn("claude-desktop-update --allow-older", r.stdout)
        self.assertEqual((self.version(), self.downloads), ("2.11.0", []))
        self.assertIn("mine", (self.opt / "claude-desktop").read_text())
        r = self.update("--allow-older")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.version(), "2.10.0")

    def test_over_https_only(self):
        """HTTPS, redirects included (curl otherwise follows one to http://), and the file's place
        taken as it is, not as a curl pattern ({} and [] in it)."""
        self.index(("claude-desktop", "2.10.0"))
        self.assertEqual(self.update().returncode, 0)
        calls = Path(f"{self.curl_log}.args").read_text().splitlines()
        self.assertEqual(len(calls), 2)                      # (the list, then the package)
        for call in calls:
            self.assertIn("--proto =https --proto-redir =https ", call)
        self.assertRegex(calls[1], r" -g[A-Za-z#]* ")

    def test_a_file_in_an_odd_place_is_refused(self):
        for where in ("pool/main/c/claude-desktop/../../../../x.deb", "pool/c/claude-desktop_{1,2}_arm64.deb",
                      "pool/c/x.deb?y=1", "https://elsewhere.test/x.deb", "/x.deb"):
            with self.subTest(where):
                self.index(("claude-desktop", "2.10.0", where))
                r = self.update()
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(f"Anthropic's package list names an unexpected file for Claude Desktop: {where}", r.stderr)
                self.assertEqual(self.downloads, [])
                self.assertFalse(self.opt.exists())

    def test_print_latest_only_says_which(self):
        """(for the installer window's update check: it offers what an update would install)"""
        self.installed("2.9.0")
        self.index(("claude-desktop-beta", "9.0.0"), ("claude-desktop", "2.10.0"), ("claude-desktop", "2.9.5"))
        r = self.update("--print-latest")
        self.assertEqual((r.returncode, r.stdout), (0, "2.10.0\n"), r.stderr)
        self.assertEqual((self.version(), self.downloads), ("2.9.0", []))
        self.assertFalse((self.home / ".local/bin/claude-desktop").exists())

    def test_a_list_without_claude_desktop(self):
        self.index(("claude-desktop-beta", "9.0.0"))
        r = self.update()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Anthropic's package list has no Claude Desktop for arm64", r.stderr)
        self.assertEqual(self.downloads, [])
        self.assertFalse(self.opt.exists())


if __name__ == "__main__":
    unittest.main()
