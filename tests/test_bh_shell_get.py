"""get.sh, the bootstrap: it installs the newest release tag of the channel (stable, or beta with
pre-releases ranked below their release), updates an existing checkout to it, says so when there
is no release, and stops (without opening the old version) when an existing checkout can't be
updated. Against a stand-in repository whose install.sh only logs how it was run."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("git"), "needs git")
class GetSh(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.log = self.tmp / "install.log"
        self.env = {"HOME": str(self.tmp / "home"), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t", "LOG": str(self.log)}
        (self.tmp / "home").mkdir()
        self.src = self.tmp / "src"
        self.git(self.tmp, "init", "-q", str(self.src))
        (self.src / "install.sh").write_text('#!/bin/bash\necho "install.sh $*" >> "$LOG"\n')
        (self.src / "install.sh").chmod(0o755)
        self.dest = self.tmp / "frame-tweaks"

    def git(self, where, *args):
        return subprocess.run(["git", "-C", str(where), *args], env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def release(self, *tags):
        for tag in tags:
            (self.src / "VERSION").write_text(tag + "\n")
            self.git(self.src, "add", "-A")
            self.git(self.src, "commit", "-qm", tag)
            self.git(self.src, "tag", "-a", tag, "-m", tag)

    def get(self, **extra):
        return subprocess.run(["bash", str(ROOT / "get.sh")], capture_output=True, text=True, timeout=60,
                              env={**self.env, "FRAME_TWEAKS_REPO": f"file://{self.src}",
                                   "FRAME_TWEAKS_DIR": str(self.dest), **extra})

    def ran(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def at(self):
        return (self.dest / "VERSION").read_text().strip()

    def test_installs_the_newest_stable_release(self):
        self.release("v0.9.0", "v0.10.0", "v0.11.0-rc.1")
        r = self.get()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.at(), "v0.10.0")
        self.assertEqual(self.ran(), ["install.sh menu", "install.sh "])     # (then the installer)

    def test_beta_takes_a_pre_release_but_not_over_its_release(self):
        self.release("v0.10.0", "v0.11.0-rc.1")
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)
        self.assertEqual(self.at(), "v0.11.0-rc.1")
        self.release("v0.11.0")
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)     # (an update)
        self.assertEqual(self.at(), "v0.11.0")

    def test_updates_an_existing_checkout(self):
        self.release("v0.9.0")
        self.assertEqual(self.get().returncode, 0)
        self.release("v0.10.0")
        r = self.get()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Updating", r.stdout)
        self.assertEqual(self.at(), "v0.10.0")

    def test_no_release_says_so(self):
        self.release("v0.11.0-rc.1")                      # (a pre-release only: none for stable)
        r = self.get()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Couldn't find a release", r.stderr)
        self.assertFalse(self.dest.exists())

    def test_a_checkout_that_cant_update_doesnt_open_the_old_version(self):
        self.release("v0.9.0")
        self.assertEqual(self.get().returncode, 0)
        self.log.unlink()
        self.release("v0.10.0")
        self.git(self.dest, "remote", "set-url", "origin", str(self.tmp / "gone"))     # (fetch fails)
        r = self.get()
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.at(), "v0.9.0")
        self.assertEqual(self.ran(), [])


if __name__ == "__main__":
    unittest.main()
