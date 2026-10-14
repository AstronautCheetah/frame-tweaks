"""lib/common.sh verify_release: ./install.sh update moves only to a release tag signed by a key
in dev/release-signers as already installed; unsigned or wrongly signed tags are refused, and a
checkout from before signing (no signers file) isn't checked. Uses throwaway SSH keys."""
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


if __name__ == "__main__":
    unittest.main()
