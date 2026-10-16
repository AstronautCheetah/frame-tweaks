"""lib/common.sh verify_release: ./install.sh update moves only to a release tag signed by a key
in dev/release-signers as already installed; unsigned or wrongly signed tags are refused (a PGP
signature, or a signed tag under another name, too), and a checkout from before signing (no
signers file) isn't checked. And the update itself (Update). Uses throwaway SSH keys."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("ssh-keygen") and shutil.which("git"), "needs ssh-keygen and git")
class VerifyRelease(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.env = {**os.environ, "HOME": str(self.tmp), "GIT_CONFIG_GLOBAL": "/dev/null",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t"}
        for k in ("release", "other"):
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", k, "-f", str(self.tmp / k)], check=True)
        self.repo = self.tmp / "repo"
        self.git("init", "-q", str(self.repo), cwd=self.tmp)
        (self.repo / "dev").mkdir()
        pub = (self.tmp / "release.pub").read_text().split()
        (self.repo / "dev/release-signers").write_text(f'release namespaces="git" {pub[0]} {pub[1]}\n')
        self.git("add", "-A")
        self.git("commit", "-qm", "one")

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=self.env, check=True,
                              capture_output=True, text=True)

    def tag(self, name, key=None):
        if key:
            self.git("-c", "gpg.format=ssh", "-c", f"user.signingkey={self.tmp / key}", "tag", "-s", name, "-m", name)
        else:
            self.git("tag", "-a", name, "-m", name)

    def verify(self, tag, **extra):
        return subprocess.run(["bash", "-c", f'source "{ROOT}/lib/common.sh"; verify_release "$1" "$2"', "_",
                               str(self.repo), tag], env={**self.env, **extra}, capture_output=True, text=True)

    def test_signed_by_the_release_key(self):
        self.tag("v1.0.0", "release")
        r = self.verify("v1.0.0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("signature verified", r.stdout)

    def test_unsigned_and_other_key_refused(self):
        self.tag("v1.0.0")
        self.tag("v1.0.1", "other")
        for t in ("v1.0.0", "v1.0.1"):
            r = self.verify(t)
            self.assertNotEqual(r.returncode, 0, t)
            self.assertIn("wasn't installed", r.stderr)
        self.assertEqual(self.verify("v1.0.0", FRAME_TWEAKS_ALLOW_UNSIGNED="1").returncode, 0)

    def test_a_release_cant_bring_its_own_key(self):
        """The new release's signers file doesn't count: only the one installed now."""
        (self.repo / "dev/release-signers").write_text("")       # installed: no key matches
        self.tag("v1.0.0", "release")
        self.assertNotEqual(self.verify("v1.0.0").returncode, 0)

    def test_checkout_from_before_signing_isnt_checked(self):
        (self.repo / "dev/release-signers").unlink()
        self.tag("v1.0.0")
        self.assertEqual(self.verify("v1.0.0").returncode, 0)

    @unittest.skipUnless(shutil.which("gpg") and shutil.which("gpgconf"), "needs gpg")
    def test_a_pgp_signature_doesnt_count(self):
        """git would check it against the user's own GPG keyring (any key in it), not the signers file."""
        (self.tmp / ".gnupg").mkdir(mode=0o700)                 # (HOME's: the user's keyring)
        self.addCleanup(subprocess.run, ["gpgconf", "--kill", "gpg-agent"], env=self.env, capture_output=True, timeout=30)
        subprocess.run(["gpg", "--batch", "--passphrase", "", "--quick-gen-key", "Someone <s@test.invalid>",
                        "ed25519", "sign", "never"], env=self.env, check=True, capture_output=True, timeout=60)
        self.git("-c", "user.signingkey=s@test.invalid", "tag", "-s", "v1.0.0", "-m", "v1.0.0")
        r = self.verify("v1.0.0")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("wasn't installed", r.stderr)

    def test_an_older_release_under_a_newer_name_is_refused(self):
        """A signed tag carries its own name: the same tag under another name doesn't pass."""
        self.tag("v1.0.0", "release")
        self.git("update-ref", "refs/tags/v2.0.0", self.git("rev-parse", "refs/tags/v1.0.0").stdout.strip())
        self.assertNotEqual(self.verify("v2.0.0").returncode, 0)
        self.assertEqual(self.verify("v1.0.0").returncode, 0)


PROBE = """\
---
title: Probe
emoji: 🧪
category: Tests
tier: extras
summary: A test tweak that does nothing
what: Nothing.
why: For tests.
author: Tests
changes: Nothing
access: None
survives_updates: "Yes"
undo: ./install.sh uninstall probe
processes: []
---
# Probe
"""


@unittest.skipUnless(shutil.which("ssh-keygen") and shutil.which("git") and shutil.which("flock"),
                     "needs ssh-keygen, git and flock")
class Update(unittest.TestCase):
    """./install.sh update in a release checkout: to the newest signed tag (checked out as the tag,
    even when a branch has its name), and stopping before the reinstall when the checkout fails.
    In a copy of this repo with two releases signed by a throwaway key, and a throwaway home with
    the official packs off (none of their scripts run) and a do-nothing tweak in their place
    (installed, it leaves a file in the home; it fails while the home has probe-fails)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, cls.tmp)
        cls.env = {"HOME": str(cls.tmp), "USER": "u", "LANG": "C.UTF-8", "GIT_CONFIG_GLOBAL": "/dev/null",
                   "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "FRAME_TWEAKS_LANGUAGE": "en",
                   "FRAME_TWEAKS_KEYBOARD": "0",
                   "PATH": os.pathsep.join([str(cls.tmp / "stubs"), os.path.dirname(shutil.which("flock")), "/usr/bin", "/bin"])}
        top = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if top.returncode == 0 and Path(top.stdout.strip()) == ROOT:        # the files git tracks
            files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True).stdout.split("\0")
        else:                                        # (not a checkout, as from a release archive: all)
            files = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                     if not {".git", "__pycache__"} & set(p.relative_to(ROOT).parts)]
        cls.src = cls.tmp / "src"                    # (the copy is "GitHub": origin of the checkouts)
        for f in filter(None, files):
            if (ROOT / f).is_file():
                (cls.src / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / f, cls.src / f)
        key = cls.tmp / "release"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "release", "-f", str(key)], check=True)
        pub = (cls.tmp / "release.pub").read_text().split()
        (cls.src / "dev/release-signers").write_text(f'release namespaces="git" {pub[0]} {pub[1]}\n')
        sign = ["-c", "gpg.format=ssh", "-c", f"user.signingkey={key}", "tag", "-s"]
        cls.git(cls.tmp, "init", "-q", str(cls.src))
        for n, tag in enumerate(("v0.0.1", "v0.0.2", "v0.0.3-rc.1"), 1):     # (the last: a test release)
            if n > 1:
                with open(cls.src / "README.md", "a") as readme:
                    readme.write(f"\nRelease {n}.\n")
            (cls.src / "VERSION").write_text(tag[1:] + "\n")                  # (as a release sets it)
            cls.git(cls.src, "add", "-A")
            cls.git(cls.src, "commit", "-qm", f"release {n}")
            cls.git(cls.src, *sign, tag, "-m", tag)
        cls.pack = cls.tmp / "probe-pack"
        (cls.pack / "probe").mkdir(parents=True)
        (cls.pack / "pack.md").write_text("---\nname: Probe pack\napi: 1\n---\n")
        (cls.pack / "probe/README.md").write_text(PROBE)
        (cls.pack / "probe/install.sh").write_text('#!/bin/bash\n[[ ! -e ~/probe-fails ]] && touch ~/probe-installed\n')
        (cls.pack / "probe/uninstall.sh").write_text('#!/bin/bash\nrm -f ~/probe-installed\n')
        (cls.pack / "probe/status.sh").write_text(
            '#!/bin/bash\n[[ -e ~/probe-installed ]] && { echo "ok       installed"; exit 0; }\necho "missing  no"; exit 1\n')
        (cls.tmp / "stubs").mkdir()
        (cls.tmp / "stubs/systemctl").write_text("#!/bin/bash\nexit 0\n")     # (sysctl_user: not the real one)
        (cls.tmp / "stubs/systemctl").chmod(0o755)

    @classmethod
    def git(cls, where, *args, check=True):
        return subprocess.run(["git", "-C", str(where), *args], env=cls.env, check=check, capture_output=True, text=True)

    def checkout(self):
        """A release checkout of v0.0.1 (as get.sh makes), and its own home."""
        d = Path(tempfile.mkdtemp(dir=self.tmp))
        self.git(d, "-c", "advice.detachedHead=false", "clone", "-q", "--branch", "v0.0.1", str(self.src), "co")
        self.home = d / "home"
        off = self.home / ".config/frame-tweaks/installer/off-packs"
        off.parent.mkdir(parents=True)
        off.write_text("integrations\noriginal\nthird-party\n")
        r = subprocess.run(["python3", str(ROOT / "lib/sft.py"), "mods", "trust", str(self.pack)],
                           env=self.run_env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        co = d / "co"
        r = subprocess.run([str(co / "install.sh"), "_deps", "all"], env=self.run_env(), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.stdout.split(), ["probe"], r.stdout + r.stderr)      # (only the probe would run)
        return co

    def run_env(self):
        return {**self.env, "HOME": str(self.home), "FRAME_TWEAKS_PACKS": str(self.pack)}

    def update(self, co, *args):
        return subprocess.run([str(co / "install.sh"), "update", *args], env=self.run_env(), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=120)

    def install(self, co, *args):
        return subprocess.run([str(co / "install.sh"), *args], env=self.run_env(), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=120)

    def recorded(self):
        return (self.home / ".local/state/frame-tweaks/installed/probe").read_text().strip()

    def channel(self, co, *args):
        return subprocess.run([str(co / "install.sh"), "channel", *args], env=self.run_env(), stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=60)

    def at(self, co):
        return self.git(co, "rev-parse", "HEAD").stdout.strip()

    def commit(self, tag):
        return self.git(self.src, "rev-parse", f"{tag}^{{commit}}").stdout.strip()

    def test_moves_to_the_newest_signed_release(self):
        co = self.checkout()
        r = self.update(co)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Release v0.0.2: signature verified.", r.stdout)
        self.assertEqual(self.at(co), self.commit("v0.0.2"))
        self.assertIn("Nothing installed yet.", r.stdout)                # (the new version's second stage)

    def test_already_the_newest_reinstalls_nothing(self):
        """The install command run again over an install is an update: on the newest release
        already, the installed tweaks' installers aren't all run again (minutes, before the window
        opened); it says how to run them anyway."""
        co = self.checkout()
        self.assertEqual(self.update(co).returncode, 0)
        r = self.update(co)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Frame Tweaks is up to date", r.stdout)
        self.assertIn("./install.sh update --reinstall", r.stdout)
        self.assertNotIn("Nothing installed yet.", r.stdout)            # (the second stage didn't run)
        self.assertNotIn("Updating to", r.stdout)
        self.assertEqual(self.at(co), self.commit("v0.0.2"))
        r = self.update(co, "--reinstall")                               # (what it says to run)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Nothing installed yet.", r.stdout)

    def test_an_update_that_didnt_finish_is_finished_by_running_it_again(self):
        """The checkout moves before the installers run: one that failed (or the update stopped
        partway) is still older, so running update again runs them, not "up to date"."""
        co = self.checkout()
        r = self.install(co, "install", "probe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.recorded(), "0.0.1")
        (self.home / "probe-fails").touch()                              # (installed, but its installer fails)
        r = self.update(co)
        self.assertIn("probe failed", r.stdout + r.stderr)
        self.assertEqual(self.at(co), self.commit("v0.0.2"))
        self.assertEqual(self.recorded(), "0.0.1")
        (self.home / "probe-fails").unlink()
        r = self.update(co)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("up to date", r.stdout)
        self.assertEqual(self.recorded(), "0.0.2")
        self.assertIn("up to date", self.update(co).stdout)             # (and then it's done)

    def test_a_held_tweak_doesnt_keep_an_update_unfinished(self):
        co = self.checkout()
        self.assertEqual(self.install(co, "install", "probe").returncode, 0)
        self.assertEqual(self.install(co, "hold", "probe").returncode, 0)
        self.assertEqual(self.update(co).returncode, 0)
        self.assertEqual(self.recorded(), "0.0.1")                      # (left as it is)
        self.assertIn("up to date", self.update(co).stdout)

    def test_test_releases_come_and_go_with_the_channel(self):
        """Beta: the test release. Stable again: no going back unasked, but --to stable goes back."""
        co = self.checkout()
        self.assertEqual(self.channel(co).stdout, "stable\n")
        r = self.channel(co, "beta")
        self.assertIn("test releases too", r.stdout)
        r = self.update(co)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.at(co), self.commit("v0.0.3-rc.1"))
        r = self.channel(co, "stable")
        self.assertIn("You're on v0.0.3-rc.1, a test release", r.stdout)
        r = self.update(co)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("you stay on it until a newer stable release is out", r.stdout)
        self.assertEqual(self.at(co), self.commit("v0.0.3-rc.1"))
        r = self.update(co, "--to", "stable")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.at(co), self.commit("v0.0.2"))
        self.assertNotEqual(self.channel(co, "nightly").returncode, 0)

    def test_a_branch_named_like_the_release_doesnt_win(self):
        co = self.checkout()
        self.git(co, "branch", "v0.0.2")                                 # (at v0.0.1)
        r = self.update(co)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.at(co), self.commit("v0.0.2"))
        self.assertNotEqual(self.git(co, "symbolic-ref", "-q", "HEAD", check=False).returncode, 0)   # (detached)

    def test_a_failed_checkout_stops_before_the_reinstall(self):
        co = self.checkout()
        (co / "README.md").write_text("Local changes, in the way of v0.0.2's\n")
        r = self.update(co)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("git checkout failed; not reinstalling", r.stdout)
        self.assertEqual(self.at(co), self.commit("v0.0.1"))
        self.assertNotIn("Nothing installed yet.", r.stdout)


if __name__ == "__main__":
    unittest.main()
