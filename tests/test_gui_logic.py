"""Pure logic of the installer window (no window is opened). Run: python3 -m unittest -v"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gui", ROOT / "gui" / "frame-tweaks-gui.py")
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


class Versions(unittest.TestCase):
    def test_version_tuple(self):
        self.assertEqual(gui.version_tuple("v1.10.2"), (1, 10, 2))
        self.assertGreater(gui.version_tuple("0.10.0"), gui.version_tuple("0.9.9"))
        self.assertEqual(gui.version_tuple(None), ())

    def test_prerelease_sorts_below_its_release(self):
        self.assertLess(gui.release_key("v1.2.0-rc1"), gui.release_key("v1.2.0"))
        self.assertLess(gui.release_key("1.2.0"), gui.release_key("1.10.0-rc1"))

    def test_newest_release_stable_ignores_prereleases(self):
        tags = ["v0.9.0", "v1.0.0-rc1", "v0.10.0", "nonsense", "v1.0"]
        self.assertEqual(gui.newest_release(tags), "0.10.0")

    def test_newest_release_beta(self):
        self.assertEqual(gui.newest_release(["v1.0.0", "v1.1.0-rc1"], "beta"), "1.1.0-rc1")
        self.assertEqual(gui.newest_release(["v1.1.0-rc1", "v1.1.0"], "beta"), "1.1.0")

    def test_channel(self):
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": "beta"}):
            self.assertEqual(gui.release_channel(), "beta")
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": "anything"}):
            self.assertEqual(gui.release_channel(), "stable")

    def test_self_update_check(self):
        out = "x\trefs/tags/v0.1.0\ny\trefs/tags/v99.0.0\nz\trefs/tags/v100.0.0-rc1\n"
        fake = subprocess.CompletedProcess([], 0, stdout=out)
        with mock.patch.object(gui.subprocess, "run", return_value=fake), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": "stable"}):
            self.assertEqual(gui.self_update_check(), "99.0.0")


class Status(unittest.TestCase):
    def test_status_text(self):
        self.assertEqual(gui.status_text(None), ("checking…", "checking"))
        self.assertEqual(gui.status_text((0, "fine")), ("✔ fine", "ok"))
        self.assertEqual(gui.status_text((2, "hmm")), ("! hmm", "warn"))
        self.assertEqual(gui.status_text((1, "")), ("· not installed", "missing"))

    def test_update_check_parsing(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(gui, "component", return_value={"dir": Path(d) / "x"}):
            (Path(d) / "x").mkdir()
            script = Path(d) / "x" / "update-check.sh"
            script.write_text("echo 1.0.0 1.1.0\n")
            self.assertEqual(gui.update_check("x"), ("1.0.0", "1.1.0"))
            script.write_text("echo 1.1.0 1.1.0\n")
            self.assertIsNone(gui.update_check("x"))
            script.write_text("echo garbage\n")
            self.assertIsNone(gui.update_check("x"))

    def test_sets_round_trip_names_with_spaces(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "sub" / "set"
            gui.write_set(f, {"Privacy & security", "System"})
            self.assertEqual(gui.read_set(f), {"Privacy & security", "System"})
        self.assertEqual(gui.read_set(Path("/nonexistent/x")), set())

    def test_latest_release_offline(self):
        with mock.patch.object(gui.urllib.request, "urlopen", side_effect=OSError("offline")):
            self.assertIsNone(gui.latest_release("https://example.invalid"))


class Manifest(unittest.TestCase):
    def test_components_parse(self):
        rows = gui.components()
        ids = [c["id"] for c in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for c in rows:
            self.assertTrue((c["dir"] / "install.sh").exists(), c["id"])
            self.assertIn(c["category"], {"Accessibility", "Convenience", "VR windows", "Privacy & security", "System", "Developer"})



class PendingChanges(unittest.TestCase):
    def test_only_real_changes_count(self):
        w = gui.Window.__new__(gui.Window)
        w.rows = [{"id": i} for i in ("a", "b", "c", "d")]
        w.state = {"a": (0, "ok"), "b": (1, "missing"), "c": (2, "warning"), "d": None}   # d: still checking
        w.wanted = {}
        self.assertEqual(w.pending_changes(), ([], []))          # nothing ticked differently
        w.wanted = {"b": True, "a": False, "c": True, "d": True}
        self.assertEqual(w.pending_changes(), (["b"], ["a"]))    # c only has a warning: not a change

class PacksPage(unittest.TestCase):
    """The Packs page lists a user's pack as not trusted; Trust… asks once more, then uses it."""
    def test_trust_from_the_page(self):
        from PyQt6.QtWidgets import QApplication, QPushButton
        self.app = QApplication.instance() or QApplication([])     # (kept: a dropped one is gone)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "packs").mkdir()
            import shutil
            shutil.copytree(ROOT / "examples/hello-pack", d / "packs" / "mine")
            with mock.patch.object(gui.sft, "USER_PACKS", d / "packs"), \
                    mock.patch.object(gui.sft, "TRUSTED", d / "trusted"), mock.patch.object(gui.sft, "CONF", d), \
                    mock.patch.dict(os.environ, {"FRAME_TWEAKS_PACKS": ""}):
                window = mock.Mock()
                page = gui.Packs(window)
                buttons = lambda: {b.text(): b for b in page.findChildren(QPushButton) if b.text() != "← Back"}
                self.assertIn("Trust…", buttons())
                buttons()["Trust…"].click()
                buttons()["Yes: it runs as me"].click()
                window.reload_tweaks.assert_called_once()
                self.assertIn("hello-frame", [c["id"] for c in gui.sft.load(refresh=True)["components"]])
                self.assertIn("Stop using", buttons())
        gui.sft.load(refresh=True)


if __name__ == "__main__":
    unittest.main()
