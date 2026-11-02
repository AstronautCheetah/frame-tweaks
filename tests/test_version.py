"""The build version people and logs see (lib/common.sh ft_version, lib/sft.py build_version):
both say the same, release tags only (not the "mirror" tag), and VERSION without git."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
import sft  # noqa: E402


def shell_version(lib):
    return subprocess.run(["bash", "-c", f'source "{lib}/common.sh"; ft_version'], capture_output=True,
                          text=True, env={**os.environ, "HOME": tempfile.gettempdir()}).stdout.strip()


class Version(unittest.TestCase):
    def test_shell_and_python_agree(self):
        v = sft.build_version()
        self.assertEqual(shell_version(ROOT / "lib"), v)
        self.assertRegex(v, r"^\d+\.\d+\.\d+(-rc\.\d+)?(\+(\d+\.)?[0-9a-f]+)?(-dirty)?$")
        self.assertTrue(v.startswith((ROOT / "VERSION").read_text().strip()))
        self.assertFalse(v.startswith("mirror"))

    def test_without_git_it_is_the_version_file(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(ROOT / "lib", Path(d) / "lib")
            (Path(d) / "VERSION").write_text("9.8.7\n")
            self.assertEqual(shell_version(Path(d) / "lib"), "9.8.7")

    def test_the_number_is_the_version_file_whatever_tags_are_reachable(self):
        """A release tag on a branch not merged yet: git describe reached an older tag and said
        0.6.21+34 while VERSION said 0.6.23."""
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            shutil.copytree(ROOT / "lib", repo / "lib")
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com", "HOME": d}

            def git(*args):
                return subprocess.run(["git", "-C", d, "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
                                       "-c", "core.hooksPath=/dev/null", *args],
                                      env=env, capture_output=True, text=True, check=True).stdout.strip()

            def commit(version):
                (repo / "VERSION").write_text(version + "\n")
                git("add", "-A")
                git("commit", "-qm", version)
                return git("rev-parse", "--short", "HEAD")
            git("init", "-q")
            commit("0.6.21")
            git("tag", "v0.6.21")
            head = commit("0.6.23")                       # (VERSION moved on; v0.6.23 is elsewhere)
            self.assertEqual(shell_version(repo / "lib"), f"0.6.23+{head}")
            git("tag", "v0.6.23")
            self.assertEqual(shell_version(repo / "lib"), "0.6.23")
            (repo / "lib" / "extra").write_text("x")
            git("add", "lib/extra")
            git("commit", "-qm", "more")
            head = git("rev-parse", "--short", "HEAD")
            self.assertEqual(shell_version(repo / "lib"), f"0.6.23+1.{head}")
            (repo / "lib" / "extra").write_text("changed")
            self.assertEqual(shell_version(repo / "lib"), f"0.6.23+1.{head}-dirty")


if __name__ == "__main__":
    unittest.main()
