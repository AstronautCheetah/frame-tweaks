"""Packs from a link (./install.sh mods add | update | remove): a pack shared as a git repository is
cloned into the packs folder and isn't used until it's trusted; an update brings its newer
version, which waits to be trusted again; remove deletes it, but not while its tweaks are
installed. Against local repositories (file://), in a throwaway home."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env  # noqa: E402


@unittest.skipUnless(shutil.which("git"), "needs git")
class PackLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = sandbox_env(self.home, path=("/usr/bin", "/bin"), FRAME_TWEAKS_PACKS="",
                               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                               GIT_COMMITTER_EMAIL="t@t")
        self.src = self.tmp / "hello-pack"                   # (someone's pack, as its repository)
        shutil.copytree(ROOT / "examples/hello-pack", self.src)
        self.git(self.src, "init", "-q", "-b", "main")
        self.commit("first")
        self.link = f"file://{self.src}"
        self.packs = self.home / ".local/share/frame-tweaks/packs"

    def git(self, where, *args):
        return subprocess.run(["git", "-C", str(where), *args], env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def commit(self, message):
        self.git(self.src, "add", "-A")
        self.git(self.src, "commit", "-qm", message)

    def mods(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "lib/sft.py"), "mods", *args], env=self.env,
                              capture_output=True, text=True, timeout=60)

    def state(self):
        out = self.mods().stdout
        return next(line for line in out.splitlines() if str(self.packs / "hello-pack") in line)

    def test_added_but_not_used_until_trusted(self):
        r = self.mods("add", self.link)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.packs / "hello-pack/hello-frame/README.md").is_file())
        self.assertIn("Tweaks: hello-frame", r.stdout)
        self.assertIn(f'./install.sh mods trust "{self.packs / "hello-pack"}"', r.stdout)
        self.assertIn("not trusted", self.state())
        r = self.mods("add", self.link)                                   # (twice: it's there)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already", r.stderr)

    def test_links_it_wont_take(self):
        for link in ("http://example.com/pack", "-uhelp", "ext::sh -c touch% /tmp/x", "~/somewhere", ""):
            r = self.mods("add", link)
            self.assertNotEqual(r.returncode, 0, link)
            self.assertIn("isn't a link to a pack", r.stderr, link)
        self.assertNotIn("isn't a branch", self.mods("add", self.link, "main").stderr)
        self.assertIn("isn't a branch or tag name", self.mods("add", self.link + "x", "--upload-pack=x").stderr)

    def test_a_repository_without_a_pack_leaves_nothing(self):
        empty = self.tmp / "notes"
        empty.mkdir()
        (empty / "notes.txt").write_text("hi\n")
        self.git(empty, "init", "-q")
        self.git(empty, "add", "-A")
        self.git(empty, "commit", "-qm", "notes")
        r = self.mods("add", f"file://{empty}")
        self.assertIn("There's no pack at the top", r.stderr)
        self.assertEqual([p.name for p in self.packs.iterdir()], [])   # (nor its half-way folder)

    def test_update_waits_for_trust_again(self):
        self.mods("add", self.link)
        self.assertEqual(self.mods("trust", str(self.packs / "hello-pack")).returncode, 0)
        r = self.mods("update", str(self.packs / "hello-pack"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("is up to date", r.stdout)
        self.assertIn("trusted: in use", self.state())
        with open(self.src / "hello-frame/install.sh", "a") as f:
            f.write("# a change\n")
        self.commit("hello-frame: a change\x1b[31m")                     # (no escape codes come through)
        r = self.mods("update", str(self.packs / "hello-pack"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("updated, 1 file changed", r.stdout)
        self.assertIn("  hello-frame: a change", r.stdout)
        self.assertNotIn("\x1b", r.stdout)
        self.assertIn("changed since you trusted it", self.state())

    def test_which_have_a_newer_version(self):
        """mods updates (and Check for updates in the window): asks where each pack came from, without
        downloading it."""
        self.assertIn("No packs added from a link", self.mods("updates").stdout)
        self.mods("add", self.link)
        self.assertIn("Hello pack: not checked: not trusted", self.mods("updates").stdout)   # (git runs only in a trusted one)
        self.mods("trust", str(self.packs / "hello-pack"))
        self.assertEqual(self.mods("updates").stdout, "Hello pack: up to date\n")
        with open(self.src / "hello-frame/install.sh", "a") as f:
            f.write("# a change\n")
        self.commit("a change")
        out = self.mods("updates").stdout
        self.assertIn("Hello pack: a newer version is out: ./install.sh mods update", out)
        self.assertNotIn("a change", self.git(self.packs / "hello-pack", "log", "--all", "--format=%s"))   # (nothing fetched)
        self.mods("update", str(self.packs / "hello-pack"))
        self.mods("trust", str(self.packs / "hello-pack"))                  # (changed: trusted again)
        self.assertEqual(self.mods("updates").stdout, "Hello pack: up to date\n")
        shutil.rmtree(self.src)                                              # (gone, or offline)
        self.assertEqual(self.mods("updates").stdout, "Hello pack: couldn't check (no connection?)\n")

    def test_a_fixed_version_has_no_updates(self):
        self.git(self.src, "tag", "v1")
        self.mods("add", self.link, "v1")
        self.mods("trust", str(self.packs / "hello-pack"))
        with open(self.src / "pack.md", "a") as f:
            f.write("\nMore.\n")
        self.commit("later")
        self.assertEqual(self.mods("updates").stdout, "Hello pack: up to date\n")

    def test_only_packs_from_a_link_update(self):
        shutil.copytree(self.src, self.packs / "copied", ignore=shutil.ignore_patterns(".git"))
        r = self.mods("update", str(self.packs / "copied"))
        self.assertIn("wasn't added from a link", r.stderr)
        self.git(self.src, "tag", "v1")
        self.mods("add", self.link, "v1")
        self.mods("trust", str(self.packs / "hello-pack"))
        r = self.mods("update", str(self.packs / "hello-pack"))
        self.assertIn("added at a fixed version", r.stderr)

    def test_remove_not_while_its_tweaks_are_installed(self):
        self.mods("add", self.link)
        self.mods("trust", str(self.packs / "hello-pack"))
        record = self.home / ".local/state/frame-tweaks/installed/hello-frame"
        record.parent.mkdir(parents=True)
        record.write_text("0.6.3\n")
        r = self.mods("remove", str(self.packs / "hello-pack"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Uninstall its tweaks first: hello-frame (./install.sh uninstall hello-frame)", r.stderr)
        self.mods("untrust", str(self.packs / "hello-pack"))
        self.assertIn("trust it again to uninstall them", self.mods("remove", str(self.packs / "hello-pack")).stderr)
        record.unlink()
        r = self.mods("remove", str(self.packs / "hello-pack"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.packs / "hello-pack").exists())
        trusted = self.home / ".config/frame-tweaks/installer/trusted-packs"
        self.assertNotIn("hello-pack", trusted.read_text() if trusted.exists() else "")

    def test_only_your_packs_are_removed(self):
        r = self.mods("remove", "Core")
        self.assertIn("Only packs in", r.stderr)
        self.assertTrue((ROOT / "packs/core").is_dir())


if __name__ == "__main__":
    unittest.main()
