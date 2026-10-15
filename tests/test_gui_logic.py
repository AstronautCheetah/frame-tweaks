"""Pure logic of the installer window (no window is opened). Run: python3 -m unittest -v"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# (as test_00_english.py does, for when this file runs alone: English, and the language the window
# announces as it's imported kept from the real programs, which would follow it)
_ANNOUNCED, _PREFERRED = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()   # (removed at the end)
for k, v in {"FRAME_TWEAKS_LANGUAGE": "en", "FRAME_TWEAKS_KEYBOARD": "0",
             "FRAME_TWEAKS_ANNOUNCE_FILE": os.path.join(_ANNOUNCED.name, "language"),
             "FRAME_TWEAKS_PREFERENCE_FILE": os.path.join(_PREFERRED.name, "language")}.items():
    os.environ.setdefault(k, v)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
gui = load_script(ROOT / "gui" / "frame-tweaks-gui.py", "gui")


class Versions(unittest.TestCase):
    def test_version_tuple(self):
        self.assertEqual(gui.version_tuple("v1.10.2")[0], (1, 10, 2))
        self.assertGreater(gui.version_tuple("0.10.0"), gui.version_tuple("0.9.9"))
        self.assertEqual(gui.version_tuple(None)[0], ())
        # a pre-release is older than its release (it used to rank 1.2.0-rc1 above 1.2.0)
        self.assertLess(gui.version_tuple("1.2.0-rc1"), gui.version_tuple("1.2.0"))
        self.assertLess(gui.version_tuple("1.2.0-rc.9"), gui.version_tuple("1.2.0-rc.10"))
        self.assertGreater(gui.version_tuple("1.2.1-rc1"), gui.version_tuple("1.2.0"))
        self.assertEqual(gui.version_tuple("0.2.0+138a59b"), gui.version_tuple("0.2.0"))   # (build metadata)

    def test_prerelease_sorts_below_its_release(self):
        self.assertLess(gui.release_key("v1.2.0-rc1"), gui.release_key("v1.2.0"))
        self.assertLess(gui.release_key("1.2.0"), gui.release_key("1.10.0-rc1"))

    def test_newest_release_stable_ignores_prereleases(self):
        tags = ["v0.9.0", "v1.0.0-rc1", "v0.10.0", "nonsense", "v1.0"]
        self.assertEqual(gui.newest_release(tags), "0.10.0")

    def test_newest_release_beta(self):
        self.assertEqual(gui.newest_release(["v1.0.0", "v1.1.0-rc1"], "beta"), "1.1.0-rc1")
        self.assertEqual(gui.newest_release(["v1.1.0-rc1", "v1.1.0"], "beta"), "1.1.0")

    def test_prerelease_numbers_count_as_numbers(self):
        # (the Release workflow tags vX.Y.Z-rc.N; ./install.sh update takes the newest by sort -V)
        self.assertLess(gui.release_key("v1.2.0-rc.9"), gui.release_key("v1.2.0-rc.10"))
        self.assertLess(gui.release_key("v1.2.0-rc.10"), gui.release_key("v1.2.0"))
        self.assertEqual(gui.newest_release(["v1.2.0-rc.9", "v1.2.0-rc.10", "v1.1.0"], "beta"), "1.2.0-rc.10")
        out = "x\trefs/tags/v1.2.0-rc.9\ny\trefs/tags/v1.2.0-rc.10\n"
        fake = subprocess.CompletedProcess([], 0, stdout=out)
        with mock.patch.object(gui.subprocess, "run", return_value=fake), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": "beta"}):
            with mock.patch.object(gui, "current_release", return_value="1.2.0-rc.10"):
                self.assertEqual(gui.self_update_check(), "")       # (not "1.2.0-rc.9 available")
            with mock.patch.object(gui, "current_release", return_value="1.2.0-rc.9"):
                self.assertEqual(gui.self_update_check(), "1.2.0-rc.10")

    def test_channel(self):
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": "beta"}):
            self.assertEqual(gui.release_channel(), "beta")
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": "anything"}):
            self.assertEqual(gui.release_channel(), "stable")
        # (or "beta" in ~/.config/frame-tweaks/channel: where README says, and lib/common.sh reads it)
        self.assertEqual(gui.CHANNEL, Path.home() / ".config/frame-tweaks/channel")
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": ""}), \
                mock.patch.object(gui, "CHANNEL", Path(d) / "channel"):
            (Path(d) / "channel").write_text("beta\n")
            self.assertEqual(gui.release_channel(), "beta")

    def test_self_update_check(self):
        out = "x\trefs/tags/v0.1.0\ny\trefs/tags/v99.0.0\nz\trefs/tags/v100.0.0-rc1\n"
        fake = subprocess.CompletedProcess([], 0, stdout=out)
        with mock.patch.object(gui.subprocess, "run", return_value=fake), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": "stable"}):
            self.assertEqual(gui.self_update_check(), "99.0.0")

    def test_check_offline_isnt_up_to_date(self):
        from concurrent.futures import Future
        offline = subprocess.CompletedProcess([], 128, stdout="", stderr="fatal: unable to access")
        with mock.patch.object(gui.subprocess, "run", return_value=offline):
            self.assertIsNone(gui.self_update_check())
        done = Future()
        done.set_result(None)
        w = gui.Window.__new__(gui.Window)                 # ⟳ Check for updates, then the answer
        w.latest_futures, w.update_futures, w.futures, w.self_update, w.update_state = {}, {}, {}, done, "checking"
        w.set_update_state, w.say = mock.Mock(), mock.Mock()
        w.collect()
        w.set_update_state.assert_called_once_with("check")
        self.assertNotIn("up to date", w.say.call_args[0][0])
        self.assertNotEqual(w.say.call_args[1].get("good"), True)


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
            self.assertIn(c["category"], {"Accessibility", "Convenience", "VR environment", "Privacy & security", "System", "Developer"})



class PendingChanges(unittest.TestCase):
    def test_only_real_changes_count(self):
        w = gui.Window.__new__(gui.Window)
        w.rows = [{"id": i} for i in ("a", "b", "c", "d")]
        w.state = {"a": (0, "ok"), "b": (1, "missing"), "c": (2, "warning"), "d": None}   # d: still checking
        w.wanted = {}
        self.assertEqual(w.pending_changes(), ([], []))          # nothing ticked differently
        w.wanted = {"b": True, "a": False, "c": True, "d": True}
        self.assertEqual(w.pending_changes(), (["b"], ["a"]))    # c only has a warning: not a change


class DryRun(unittest.TestCase):
    """FRAME_TWEAKS_DRY_RUN=1: the window says what it would run, and runs nothing."""
    def test_run_button(self):
        comp = next(c for c in gui.components() if gui.run_label(c["id"]) and c["id"] not in gui.PAGES)
        w = gui.Window.__new__(gui.Window)
        with mock.patch.object(gui, "QProcess") as qprocess, mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            w.run(comp)
        qprocess.startDetached.assert_not_called()
        self.assertIn("would run: bash", out.getvalue())


class Terminal(unittest.TestCase):
    """Apply, ↻ and Update run in a Konsole window of their own: closing the installer window,
    which kills its QProcess, mustn't take that terminal, and the install in it, along."""
    def test_terminal_outlives_the_window(self):
        from PyQt6.QtCore import QProcess
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            konsole = d / "konsole"          # (a stand-in: runs what -e says, as the terminal would)
            konsole.write_text('#!/bin/bash\nexport TERMINAL=$$\nwhile [ "$1" != -e ]; do shift; done\nshift\n"$@"\n')
            konsole.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": f"{d}:{os.environ['PATH']}"}):
                proc = QProcess()
                # (the "install" gets to the end only while its terminal is still there)
                gui.in_terminal(proc, f'sleep 1; kill -0 "$TERMINAL" && touch {d}/done')
                self.assertTrue(proc.waitForStarted(5000))
                time.sleep(0.3)
                proc.kill()                      # what closing the window does to it
                proc.waitForFinished(5000)
            for _ in range(100):
                if (d / "done").exists():
                    break
                time.sleep(0.1)
            self.assertTrue((d / "done").exists())


class PageActions(unittest.TestCase):
    """A settings action (the Speech engine's Apply: a download) keeps running when its page is
    closed, its end leaves the closed page alone (that showed the error page), and the page
    opened again meanwhile doesn't start a second one."""
    def test_back_during_an_action(self):
        from PyQt6.QtCore import QCoreApplication, QEvent
        from PyQt6.QtWidgets import QApplication, QLabel, QWidget
        self.app = QApplication.instance() or QApplication([])
        errors = []
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "act.sh").write_text(f"echo run >> {d}/runs; sleep 0.5; touch {d}/done; echo Done\n")
            spec = {"file": d / "x.json", "format": "json", "about": "", "note": "", "options": [],
                    "actions": [], "checkboxes": set(), "swatches": set(), "include": []}
            with mock.patch.dict(gui.sft.SETTINGS, {"x-test": spec}), mock.patch.dict(os.environ), \
                    mock.patch.object(sys, "excepthook", lambda *a: errors.append(a[1])):
                os.environ.pop("FRAME_TWEAKS_DRY_RUN", None)
                window = QWidget()

                def page():
                    p = QWidget(window)
                    section = gui.SettingsSection("x-test", QLabel(p))
                    section.setParent(p)
                    return p, section
                first, section = page()
                section.act({"dir": d, "script": "act.sh"})
                first.deleteLater()              # ← Back
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                again, section = page()
                section.act({"dir": d, "script": "act.sh"})
                running = lambda: [p for p in window.findChildren(gui.QProcess)
                                   if p.state() != gui.QProcess.ProcessState.NotRunning]
                for _ in range(200):
                    self.app.processEvents()     # (its finished signal, once it's done)
                    if (d / "done").exists() and not running():
                        break
                    time.sleep(0.05)
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.assertTrue((d / "done").exists())
            self.assertEqual((d / "runs").read_text(), "run\n")
            self.assertEqual(errors, [])

class Links(unittest.TestCase):
    """Each web or file link gets a 📋 that copies it; the details page's README links are absolute."""
    def test_with_copy(self):
        out = gui.with_copy("<a href='https://x.org/a?b=1'>x</a> and <a href=\"file:///tmp/r.md\">r</a> "
                            "<a href='update'>Update</a>")
        self.assertIn("href='copy:https://x.org/a?b=1'", out)
        self.assertIn('href="copy:file:///tmp/r.md"', out)
        self.assertNotIn("copy:update", out)
        self.assertNotIn("copy:copy:", gui.with_copy(out))      # a 📋 isn't given one of its own
        self.assertEqual(gui.md_text("runs [x](https://e.org/a) & <b>"),
                         "runs <a style='color:#7fb2e5' href='https://e.org/a'>x</a> &amp; &lt;b&gt;")

    def test_copy_and_details_page(self):
        from PyQt6.QtWidgets import QApplication, QTextBrowser
        self.app = QApplication.instance() or QApplication([])
        gui.follow_link("copy:https://example.com/x#y")
        self.assertEqual(QApplication.clipboard().text(), "https://example.com/x#y")
        window = mock.Mock(latest={})
        page = gui.Details(window, gui.component("clipboard"), None)
        html = page.findChild(QTextBrowser).toHtml()
        self.assertIn("copy:https://github.com/", html)
        self.assertNotIn('href="../', html)

    def test_link_to_a_heading_scrolls_there(self):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        text = "See [Build from source](#build-from-source).\n\n" + "Filler.\n\n" * 80 + "## Build From Source\n\nHere.\n"
        view = gui.readme_browser(text, {"official": True, "id": None, "dir": gui.REPO})
        view.resize(400, 200)
        view.show()
        self.app.processEvents()
        with mock.patch.object(gui, "follow_link") as follow:
            view.anchorClicked.emit(QUrl("#build-from-source"))
        follow.assert_not_called()                   # (not handed to the desktop as "#build-from-source")
        self.assertGreater(view.verticalScrollBar().value(), 0)


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



class PreferencesPage(unittest.TestCase):
    """⚙ Preferences → Uninstalling a tweak: the choice lands in the file ./install.sh uninstall
    reads, and the confirmation before removing says what happens to the settings."""
    def test_uninstall_choice(self):
        from PyQt6.QtWidgets import QApplication, QPushButton
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d:
            pref = Path(d) / "uninstall-settings"
            with mock.patch.object(gui.sft, "UNINSTALL_PREF", pref):
                window = mock.Mock()
                page = gui.Preferences(window)
                buttons = {b.text(): b for b in page.findChildren(QPushButton)}
                self.assertTrue(buttons["Keep its settings"].isChecked())       # (the default)
                self.assertFalse(buttons["Remove its settings too"].isChecked())
                buttons["Remove its settings too"].click()
                self.assertEqual(pref.read_text(), "remove\n")
                self.assertEqual(gui.sft.uninstall_settings(), "remove")
                self.assertFalse(buttons["Keep its settings"].isChecked())
                buttons["Keep its settings"].click()
                self.assertEqual(gui.sft.uninstall_settings(), "keep")
                self.assertFalse(buttons["Remove its settings too"].isChecked())

    def test_deleting_what_uninstalled_tweaks_left(self):
        """Only tweaks known not to be installed: one still being checked counts as installed."""
        from PyQt6.QtWidgets import QApplication, QPushButton
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            for p in (".config/arrowpad.json", ".config/frame-tweaks/snip.json", ".config/frame-tweaks/dictate.conf"):
                (home / p).parent.mkdir(parents=True, exist_ok=True)
                (home / p).write_text("{}")
            with mock.patch.object(Path, "home", lambda: home):
                window = mock.Mock()
                window.state = {"arrowpad": (1, "not installed"), "snip": (0, "ok")}       # (dictation: not known yet)
                page = gui.Preferences(window)
                buttons = {b.text(): b for b in page.findChildren(QPushButton)}
                buttons["Delete settings left by uninstalled tweaks…"].click()
                self.assertFalse(page.leftovers.isHidden())
                self.assertIn("Arrow Pad: ~/.config/arrowpad.json", page.leftovers.text.text())
                self.assertNotIn("snip.json", page.leftovers.text.text())
                self.assertNotIn("dictate.conf", page.leftovers.text.text())
                page.leftovers.yes.click()
                self.assertFalse((home / ".config/arrowpad.json").exists())
                self.assertTrue((home / ".config/frame-tweaks/snip.json").exists())
                self.assertTrue((home / ".config/frame-tweaks/dictate.conf").exists())
                window.say.assert_called_with("Deleted 1 setting.", good=True)
                buttons["Delete settings left by uninstalled tweaks…"].click()          # nothing left now
                window.say.assert_called_with("No settings left behind by uninstalled tweaks.", good=True)

    def test_uninstall_frame_tweaks_asks_then_hands_over(self):
        from PyQt6.QtWidgets import QApplication, QCheckBox, QPushButton
        self.app = QApplication.instance() or QApplication([])
        window = mock.Mock()
        page = gui.Preferences(window)
        buttons = {b.text(): b for b in page.findChildren(QPushButton)}
        boxes = {b.text(): b for b in page.findChildren(QCheckBox)}
        self.assertTrue(boxes["Uninstall every tweak first"].isChecked())
        boxes["Uninstall every tweak first"].setChecked(False)
        boxes["Delete the settings too"].setChecked(True)
        buttons["Uninstall Frame Tweaks…"].click()
        self.assertIn("The tweaks stay installed.", page.leaving.text.text())
        self.assertIn("Settings are deleted.", page.leaving.text.text())
        window.uninstall_self.assert_not_called()                     # (asked first)
        page.leaving.yes.click()
        window.uninstall_self.assert_called_once_with(keep_tweaks=True, settings="remove", keep_apps=True)
        self.assertFalse(boxes["Leave third-party apps installed"].isEnabled())        # (only with the tweaks going)
        boxes["Uninstall every tweak first"].setChecked(True)
        self.assertTrue(boxes["Leave third-party apps installed"].isChecked())          # (safe by default)
        boxes["Leave third-party apps installed"].setChecked(False)
        buttons["Uninstall Frame Tweaks…"].click()
        self.assertIn("third-party apps too", page.leaving.text.text())
        page.leaving.yes.click()
        window.uninstall_self.assert_called_with(keep_tweaks=False, settings="remove", keep_apps=False)

    def test_window_runs_uninstall_self_as_planned(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}), contextlib.redirect_stdout(out):
            gui.Window.uninstall_self(mock.Mock(), keep_tweaks=False, settings="keep")
            gui.Window.uninstall_self(mock.Mock(), keep_tweaks=False, settings="keep", keep_apps=False)
        self.assertEqual(out.getvalue().split("\n")[:2], ["would run: ./install.sh uninstall-self --keep-settings",
                                                           "would run: ./install.sh uninstall-self --remove-apps --keep-settings"])


if __name__ == "__main__":
    unittest.main()
