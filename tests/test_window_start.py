"""./install.sh gui never ends with nothing on screen: setting up PyQt6 happens where it can be
seen (a Konsole window of its own, started from the app menu), and a window that ends with an
error before it's shown leaves the simple checklist instead, saying so; both go to
logs/window.log. In a throwaway home: a stand-in Python, kdialog and konsole record what they're
asked."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402


class WindowStart(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.stubs = self.home / "stubs"
        self.calls = self.home / "calls"
        for tool in ("kdialog", "konsole", "notify-send"):
            # (kdialog: yes to the setup question, cancel for the checklist)
            stub(self.stubs, tool, f'echo "{tool} $*" >> {self.calls}\n'
                                   '[ "$1" = --title ] && [ "$3" = --yesno ] && exit 0\n'
                                   'case "$*" in *--checklist*) exit 1 ;; esac; exit 0')
        self.venv = self.home / ".local/share/arrowpad/venv/bin"
        self.venv.mkdir(parents=True)

    def python(self, has_pyqt, window):
        """The shared venv's Python: PyQt6 there or not; the window's own run (a script)."""
        p = self.venv / "python"
        p.write_text("#!/bin/bash\n" + f'[ "$1" = -c ] && exit {0 if has_pyqt else 1}\n' + window + "\n")
        p.chmod(0o755)

    def gui(self):
        env = sandbox_env(self.home, self.stubs, DISPLAY=":9", FRAME_TWEAKS_PACKS="")
        return subprocess.run([str(ROOT / "install.sh"), "gui"], env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=60)

    def log(self):
        return (self.home / ".local/state/frame-tweaks/logs/window.log").read_text()

    def test_a_window_that_doesnt_open_leaves_the_checklist(self):
        self.python(True, 'echo "Traceback: no display" >&2; exit 1')
        r = self.gui()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = self.calls.read_text()
        self.assertIn("kdialog --sorry The full window didn't open", calls)
        self.assertIn("--checklist", calls)                     # (the simple checklist instead)
        self.assertIn("Traceback: no display", self.log())
        self.assertIn("the window ended with 1", self.log())

    def test_a_window_closed_as_usual_leaves_nothing_more(self):
        self.python(True, "exit 0")
        r = self.gui()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("--sorry", self.calls.read_text() if self.calls.exists() else "")
        self.assertNotIn("--checklist", self.calls.read_text() if self.calls.exists() else "")

    def test_from_the_app_menu_the_setup_has_a_window_of_its_own(self):
        self.python(False, "exit 0")                            # (the stand-in konsole sets up nothing)
        r = self.gui()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = self.calls.read_text()
        self.assertIn("It needs PyQt6, the toolkit it's drawn with", calls)
        self.assertIn(f"konsole --separate -e {ROOT}/install.sh _setup-window", calls)
        self.assertIn("kdialog --sorry Couldn't install PyQt6", calls)
        self.assertIn("--checklist", calls)
        self.assertIn("setting up PyQt6 for the full window", self.log())


if __name__ == "__main__":
    unittest.main()
