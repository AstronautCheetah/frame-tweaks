"""get.sh, the bootstrap: it installs the newest release tag of the channel (stable, or beta with
pre-releases ranked below their release; given, or kept from before), says so when there is no
release, runs install.sh by its full path (FRAME_TWEAKS_DIR relative too), and on an existing
checkout runs ./install.sh update (signature check and all), stopping, without opening the old
version, when that fails. Against a stand-in repository whose install.sh only logs how it was run
(and fails "update" when FAIL_UPDATE is set)."""
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
        (self.src / "install.sh").write_text('#!/bin/bash\necho "install.sh $*" >> "$LOG"\necho "$0" >> "$LOG.run-as"\n'
                                             '[ "${1:-}" = update ] && [ -n "${FAIL_UPDATE:-}" ] && exit "$FAIL_UPDATE"; exit 0\n')
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

    def test_the_channel_given_is_kept_for_updates(self):
        """The testers' link (FRAME_TWEAKS_CHANNEL=beta) is remembered: updates take test releases too."""
        self.release("v0.10.0", "v0.11.0-rc.1")
        channel = self.tmp / "home/.config/frame-tweaks/channel"
        self.assertEqual(self.get().returncode, 0)
        self.assertFalse(channel.exists())                            # (none given: none written)
        shutil.rmtree(self.dest)
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)
        self.assertEqual(channel.read_text(), "beta\n")
        r = self.get(FRAME_TWEAKS_CHANNEL="stable")                    # (installed: an update)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(channel.read_text(), "stable\n")
        r = self.get(FRAME_TWEAKS_CHANNEL="nightly")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stable or beta", r.stderr)

    def test_a_channel_kept_from_before_counts_for_a_new_install(self):
        """Installed again (its settings kept): ~/.config/frame-tweaks/channel says beta, as updates
        read it, unless FRAME_TWEAKS_CHANNEL says otherwise."""
        self.release("v0.10.0", "v0.11.0-rc.1")
        channel = self.tmp / "home/.config/frame-tweaks/channel"
        channel.parent.mkdir(parents=True)
        channel.write_text("beta\n")
        r = self.get()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.at(), "v0.11.0-rc.1")
        shutil.rmtree(self.dest)
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="stable").returncode, 0)
        self.assertEqual(self.at(), "v0.10.0")

    def test_a_relative_folder(self):
        """FRAME_TWEAKS_DIR=frame-tweaks, relative: install.sh is run by its full path (by a
        relative one with a folder in it, it couldn't find itself)."""
        self.release("v0.10.0")
        r = subprocess.run(["bash", str(ROOT / "get.sh")], cwd=self.tmp, capture_output=True, text=True, timeout=60,
                           env={**self.env, "FRAME_TWEAKS_REPO": f"file://{self.src}", "FRAME_TWEAKS_DIR": "frame-tweaks"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.at(), "v0.10.0")
        self.assertEqual(self.ran(), ["install.sh menu", "install.sh "])
        self.assertEqual(Path(f"{self.log}.run-as").read_text().split(), [str(self.dest / "install.sh")] * 2)

    def test_beta_takes_a_pre_release_but_not_over_its_release(self):
        self.release("v0.10.0", "v0.11.0-rc.1")
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)
        self.assertEqual(self.at(), "v0.11.0-rc.1")
        self.release("v0.11.0")
        shutil.rmtree(self.dest)                          # (a new install: an update is install.sh's)
        self.assertEqual(self.get(FRAME_TWEAKS_CHANNEL="beta").returncode, 0)
        self.assertEqual(self.at(), "v0.11.0")

    def test_an_existing_checkout_is_updated_by_install_sh(self):
        """With its checks: the signature against this copy's release key, the installers again."""
        self.release("v0.9.0")
        self.assertEqual(self.get().returncode, 0)
        self.log.unlink()
        self.release("v0.10.0")
        r = self.get()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Updating", r.stdout)
        self.assertEqual(self.ran(), ["install.sh update", "install.sh menu", "install.sh "])

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
        r = self.get(FAIL_UPDATE="1")                      # (say, a release that isn't signed)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.at(), "v0.9.0")
        self.assertEqual(self.ran(), ["install.sh update"])


    def test_an_update_where_a_tweak_failed_still_opens_the_window(self):
        """update's exit 3: Frame Tweaks updated, but a tweak didn't install again. The window
        shows which, so it's opened, unlike an update that couldn't happen."""
        self.release("v0.9.0")
        self.assertEqual(self.get().returncode, 0)
        self.log.unlink()
        self.release("v0.10.0")
        r = self.get(FAIL_UPDATE="3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Some tweaks didn't update", r.stdout)
        self.assertEqual(self.ran(), ["install.sh update", "install.sh menu", "install.sh "])


if __name__ == "__main__":
    unittest.main()
