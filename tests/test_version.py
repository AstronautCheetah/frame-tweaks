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
        self.assertRegex(v, r"^\d+\.\d+\.\d+(-rc\.\d+)?(\+\d+\.[0-9a-f]+)?(-dirty)?$")
        self.assertFalse(v.startswith("mirror"))

    def test_without_git_it_is_the_version_file(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(ROOT / "lib", Path(d) / "lib")
            (Path(d) / "VERSION").write_text("9.8.7\n")
            self.assertEqual(shell_version(Path(d) / "lib"), "9.8.7")


if __name__ == "__main__":
    unittest.main()
