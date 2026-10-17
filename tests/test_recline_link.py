"""Recline (a linked project): its uninstall removes ~/Recline-VR only if Frame Tweaks cloned it
(its install marks the clone) and it holds nothing of yours: install took over a clone you had
already, and uninstall deleted it, local commits and changes included. Its own commands, as the
manifest has them, in a throwaway home with a stand-in Recline-VR uninstaller."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT  # noqa: E402


def link_command(action):
    return subprocess.run([sys.executable, str(ROOT / "lib/sft.py"), "link", "recline", action],
                          capture_output=True, text=True, check=True).stdout.strip()


class ReclineUninstall(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(HOME=str(self.home), GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        upstream = self.home / "upstream.git"
        self.git("init", "-q", "--bare", "-b", "main", str(upstream))
        seed = self.home / "seed"
        self.git("clone", "-q", str(upstream), str(seed))
        self.git("-C", str(seed), "commit", "-q", "--allow-empty", "-m", "x")
        self.git("-C", str(seed), "push", "-q", "origin", "HEAD:main")
        self.upstream = upstream

    def git(self, *args):
        subprocess.run(["git", *args], env=self.env, check=True, capture_output=True)

    def clone(self, ours, change=None):
        clone = self.home / "Recline-VR"
        self.git("clone", "-q", str(self.upstream), str(clone))
        if ours:
            (clone / ".git/frame-tweaks-cloned").touch()
        if change == "edit":
            (clone / "mine.txt").write_text("mine\n")
        elif change == "commit":
            self.git("-C", str(clone), "commit", "-q", "--allow-empty", "-m", "mine")
        return clone

    def uninstall(self):
        tool = self.home / ".local/share/recline-vr/uninstall.sh"       # (Recline-VR's own: a stand-in)
        tool.parent.mkdir(parents=True, exist_ok=True)
        tool.write_text("#!/bin/sh\nexit 0\n")
        tool.chmod(0o755)
        subprocess.run(["bash", "-c", link_command("uninstall")], env=self.env, check=True)

    def test_a_clone_of_yours_stays(self):
        for ours, change, stays in ((False, None, True), (True, None, False), (True, "edit", True), (True, "commit", True)):
            with self.subTest(ours=ours, change=change):
                clone = self.clone(ours, change)
                self.uninstall()
                self.assertEqual(clone.exists(), stays)
                subprocess.run(["rm", "-rf", str(clone)], check=True)

    def test_its_install_marks_the_clone_it_makes(self):
        self.assertIn("&& touch ~/Recline-VR/.git/frame-tweaks-cloned; fi", link_command("install"))


class ReclineUpdateCheck(unittest.TestCase):
    """Its update-check.sh: the installed VERSION against where GitHub's latest-release link leads
    (a stand-in curl), as "<installed> <newest>" for the window's update hint, or nothing."""
    SCRIPT = ROOT / "packs/third-party/recline/update-check.sh"

    def run_check(self, version, headers="HTTP/2 302\r\nlocation: https://github.com/new-waifu/Recline-VR/releases/tag/v1.4.0\r\n\r\n"):
        with tempfile.TemporaryDirectory() as d:
            home, bin_ = Path(d, "home"), Path(d, "bin")
            bin_.mkdir()
            curl = bin_ / "curl"
            curl.write_text("#!/bin/sh\nprintf '%s' \"$HEADERS\"\n" if headers else "#!/bin/sh\nexit 6\n")
            curl.chmod(0o755)
            if version is not None:
                (home / ".local/share/recline-vr").mkdir(parents=True)
                (home / ".local/share/recline-vr/VERSION").write_text(version + "\n")
            env = dict(os.environ, HOME=str(home), PATH=f"{bin_}:{os.environ['PATH']}", HEADERS=headers or "")
            return subprocess.run(["bash", str(self.SCRIPT)], env=env, capture_output=True, text=True).stdout

    def test_versions(self):
        for version, want in (("v1.3.0", "1.3.0 1.4.0\n"),
                              ("v1.4.0", "1.4.0 1.4.0\n"),
                              ("v1.3.0+3.14d0169-dirty", "1.3.0+3.14d0169 1.4.0\n"),
                              ("unknown+14d0169", ""),          # (no tag to compare)
                              (None, "")):                      # (not installed)
            with self.subTest(version=version):
                self.assertEqual(self.run_check(version), want)

    def test_offline_says_nothing(self):
        self.assertEqual(self.run_check("v1.3.0", headers=None), "")
        self.assertEqual(self.run_check("v1.3.0", headers="HTTP/2 404\r\n\r\n"), "")


if __name__ == "__main__":
    unittest.main()
