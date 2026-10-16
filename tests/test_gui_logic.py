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
        self.assertEqual(gui.sft.CHANNEL, Path.home() / ".config/frame-tweaks/channel")
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": ""}), \
                mock.patch.object(gui.sft, "CHANNEL", Path(d) / "channel"):
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
        w.pack_check = None
        w.set_update_state, w.say = mock.Mock(), mock.Mock()
        w.collect()
        w.set_update_state.assert_called_once_with("check")
        self.assertNotIn("up to date", w.say.call_args[0][0])
        self.assertNotEqual(w.say.call_args[1].get("good"), True)

    def test_a_row_is_checked_again(self):
        """After Run (a Restart, say), and on coming back to the window: that row's status again,
        once at a time."""
        from concurrent.futures import Future
        w = gui.Window.__new__(gui.Window)
        w.rows, w.futures = [{"id": "clipboard"}], {}
        done = Future()
        done.set_result((0, "running"))
        w.pool, w.collecting = mock.Mock(), mock.Mock()
        w.pool.submit.return_value = done
        w.recheck("clipboard")
        w.recheck("clipboard")                                  # (still being checked: once)
        w.recheck("not-a-row")
        self.assertEqual(w.pool.submit.call_args_list, [mock.call(gui.status, "clipboard")])
        self.assertIs(w.futures["clipboard"], done)
        w.collecting.assert_called_once()

    def test_updated_under_an_open_window(self):
        """Nothing newer on GitHub, but the checkout changed since the window opened (an update in a
        terminal, a git pull): not "up to date" with the older build in its title, but ↻ Restart."""
        from concurrent.futures import Future
        for now, state, says in (("0.6.4+1.def5678", "restart", "updated to 0.6.4+1.def5678 since this window opened"),
                                 ("0.6.3+19.abc1234", "check", "up to date (0.6.3+19.abc1234)")):
            done = Future()
            done.set_result("")
            w = gui.Window.__new__(gui.Window)
            w.latest_futures, w.update_futures, w.futures, w.self_update, w.update_state = {}, {}, {}, done, "checking"
            w.pack_check, w.build_at_start = None, "0.6.3+19.abc1234"
            w.set_update_state, w.say = mock.Mock(), mock.Mock()
            with mock.patch.object(gui.sft, "build_version", return_value=now):
                w.collect()
            w.set_update_state.assert_called_once_with(state)
            self.assertIn(says, w.say.call_args[0][0])

    def test_packs_with_a_newer_version(self):
        """Check for updates also asks where packs added from a link came from: the window says how
        many have a newer version, linking to the Packs page."""
        from concurrent.futures import Future
        from PyQt6.QtWidgets import QApplication, QLabel
        self.app = QApplication.instance() or QApplication([])
        found = Future()
        found.set_result([{"dir": Path("/p/one")}, {"dir": Path("/p/two")}])
        w = gui.Window.__new__(gui.Window)
        w.latest_futures, w.update_futures, w.futures, w.self_update, w.details = {}, {}, {}, None, None
        w.pack_check, w.pack_update_label, w.pack_updates = found, QLabel(), set()
        w.collect()
        self.assertEqual(w.pack_updates, {Path("/p/one"), Path("/p/two")})
        self.assertIn("2 pack updates", w.pack_update_label.text())
        self.assertIn("href='packs'", w.pack_update_label.text())
        self.assertIsNone(w.pack_check)
        w.pack_updates = set()
        w.show_pack_updates()
        self.assertEqual(w.pack_update_label.text(), "")


class Status(unittest.TestCase):
    def test_status_text(self):
        self.assertEqual(gui.status_text(None), ("checking…", "checking"))
        self.assertEqual(gui.status_text((0, "fine")), ("✔ fine", "ok"))
        self.assertEqual(gui.status_text((2, "hmm")), ("! hmm", "warn"))
        self.assertEqual(gui.status_text((1, "")), ("· not installed", "missing"))
        self.assertEqual(gui.status_text((gui.RESTART, "load")), ("⟳ load", "warn"))
        self.assertEqual(gui.status_text((gui.UNLOAD, "unload")), ("⟳ unload", "warn"))

    def test_restart_line(self):
        """status.sh's "restart" line is a status of its own: installed (exit 2) or uninstalled (exit 1);
        other lines keep their code."""
        for out, code, want in (("restart  Load it\n", 2, (gui.RESTART, "Load it")), ("warning  Hmm\n", 2, (2, "Hmm")),
                                ("restart  Unload it\n", 1, (gui.UNLOAD, "Unload it")), ("missing  No\n", 1, (1, "No")),
                                ("ok       Fine\n", 0, (0, "Fine")), ("restart  x\n", 0, (0, "x"))):
            done = subprocess.CompletedProcess([], code, stdout=out, stderr="")
            with mock.patch.object(gui.subprocess, "run", return_value=done):
                self.assertEqual(gui.status("adb-scrcpy"), want, out)

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
            self.assertIsNotNone(gui.sft.script(c, "install"), c["id"])     # (its install.sh, or a link's)
            self.assertIn(c["category"], {"Accessibility", "Convenience", "VR environment", "Privacy & security", "System", "Hardware", "Developer"})



class PendingChanges(unittest.TestCase):
    def test_only_real_changes_count(self):
        w = gui.Window.__new__(gui.Window)
        w.rows = [{"id": i} for i in ("a", "b", "c", "d", "e")]
        w.state = {"a": (0, "ok"), "b": (1, "missing"), "c": (2, "warning"), "d": None,   # d: still checking
                   "e": (gui.UNLOAD, "uninstalled; restart SteamVR")}                     # e: not installed
        w.wanted = {}
        self.assertEqual(w.pending_changes(), ([], []))          # nothing ticked differently
        w.wanted = {"b": True, "a": False, "c": True, "d": True}
        self.assertEqual(w.pending_changes(), (["b"], ["a"]))    # c only has a warning: not a change
        w.wanted = {"e": True}
        self.assertEqual(w.pending_changes(), (["e"], []))


class DryRun(unittest.TestCase):
    """FRAME_TWEAKS_DRY_RUN=1: the window says what it would run, and runs nothing."""
    def test_run_button(self):
        comp = next(c for c in gui.components() if gui.run_label(c["id"]) and c["id"] not in gui.PAGES)
        w = gui.Window.__new__(gui.Window)
        w.state = {comp["id"]: (0, "fine")}
        with mock.patch.object(gui, "QProcess") as qprocess, mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            w.run(comp)
        qprocess.startDetached.assert_not_called()
        self.assertIn("would run: bash", out.getvalue())

    def test_restart_steamvr_button(self):
        """Waiting for a SteamVR restart: the row's button (Settings here) restarts SteamVR, once asked."""
        from PyQt6.QtWidgets import QApplication, QPushButton, QStackedWidget
        self.app = QApplication.instance() or QApplication([])
        comp = next(c for c in gui.components() if c["id"] in gui.SETTINGS_PAGES and not gui.run_label(c["id"]))
        w = gui.Window.__new__(gui.Window)
        w.state, w.run_buttons = {comp["id"]: (gui.RESTART, "load it")}, {comp["id"]: QPushButton()}
        w.stack = QStackedWidget()
        w.stack.addWidget(QPushButton())                 # (the list)
        w.confirm_page, w.confirm_text, w.confirm_yes = w.make_confirm_page()
        w.stack.addWidget(w.confirm_page)
        w.update_run(comp["id"])
        self.assertEqual(w.run_buttons[comp["id"]].text(), "⟳ Restart SteamVR")
        with mock.patch.object(gui, "QProcess") as qprocess, mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            w.run(comp)
            self.assertIs(w.stack.currentWidget(), w.confirm_page)
            self.assertIn("Every open app closes", w.confirm_text.text())
            self.assertEqual(out.getvalue(), "")                # (asks first)
            self.assertEqual(w.confirm_yes.text(), "Restart SteamVR")
            w.confirm_yes.click()
        qprocess.startDetached.assert_not_called()
        self.assertEqual(out.getvalue(), "would run: steamvr restart\n")
        self.assertEqual(w.stack.currentIndex(), 0)
        w.state[comp["id"]] = (0, "loaded")                    # restarted: Settings again
        w.update_run(comp["id"])
        self.assertEqual(w.run_buttons[comp["id"]].text(), "⚙ Settings")
        w.state[comp["id"]] = (gui.UNLOAD, "uninstalled")      # uninstalled, SteamVR still runs it: the button again
        w.update_run(comp["id"])
        self.assertEqual(w.run_buttons[comp["id"]].text(), "⟳ Restart SteamVR")
        self.assertTrue(w.run_buttons[comp["id"]].isEnabled())


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

    def test_add_update_and_remove_from_a_link(self):
        """A pack's link: Add brings it in, not trusted; one Check for updates found newer says so, and
        Update gets it; Remove… asks once more."""
        import shutil
        from PyQt6.QtWidgets import QApplication, QPushButton
        self.app = QApplication.instance() or QApplication([])
        git_env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t",
                   "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
                   "FRAME_TWEAKS_PACKS": ""}
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, git_env):
            d = Path(d)
            src = d / "their-pack"
            shutil.copytree(ROOT / "examples/hello-pack", src)
            for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "pack"]):
                subprocess.run(["git", "-C", str(src), *args], check=True, capture_output=True)
            with mock.patch.object(gui.sft, "USER_PACKS", d / "packs"), mock.patch.object(gui.sft, "CONF", d), \
                    mock.patch.object(gui.sft, "TRUSTED", d / "trusted"), \
                    mock.patch.object(gui.sft, "INSTALLED", d / "installed"):
                window = mock.Mock()
                page = gui.Packs(window)
                buttons = lambda: {b.text(): b for b in page.findChildren(QPushButton) if b.isVisibleTo(page)}

                def wait():
                    for _i in range(300):
                        QApplication.processEvents()
                        if page.job is None:
                            return
                        time.sleep(0.02)
                    self.fail("still busy")
                from PyQt6.QtWidgets import QLabel
                import packs_page
                shared = [w for w in page.findChildren(QLabel) if packs_page.COMMUNITY in w.text()]
                self.assertEqual(len(shared), 1)                      # (Packs others share ↗)
                buttons()["Add"].click()
                self.assertIn("Paste or type the link", page.notice.text())
                page.link.setText(f"file://{src}")
                buttons()["Add"].click()
                wait()
                self.assertIn("Added Hello pack. It isn't used until you trust it", page.notice.text())
                self.assertTrue((d / "packs/their-pack/pack.md").is_file())
                self.assertIn("Trust…", buttons())
                window.pack_updates = {(d / "packs/their-pack").resolve()}     # (Check for updates found one)
                page.build()
                self.assertTrue(any("A newer version is out" in w.text() for w in page.findChildren(QLabel)))
                buttons()["Update"].click()
                wait()
                self.assertEqual(page.notice.text(), "Hello pack is up to date.")
                self.assertEqual(window.pack_updates, set())                     # (got it: the notice goes)
                window.show_pack_updates.assert_called()
                buttons()["Remove…"].click()
                buttons()["Yes, delete it"].click()
                self.assertEqual(page.notice.text(), "Removed Hello pack.")
                self.assertFalse((d / "packs/their-pack").exists())
                window.reload_tweaks.assert_called()
        gui.sft.load(refresh=True)



class PackInventory(unittest.TestCase):
    """Packs page: clicking a pack's row shows what's in it (each tweak's name, tags, summary, and
    whether it's installed), again to hide it; a tweak's name opens its page, whose Back comes
    back to Packs."""
    def test_click_shows_its_tweaks(self):
        from PyQt6.QtCore import QPoint
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QApplication, QLabel
        import packs_page
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d, mock.patch.object(gui.sft, "INSTALLED", Path(d)):
            (Path(d) / "recline").write_text("0.6.4\n")                     # (an install record)
            window = mock.Mock()
            page = gui.Packs(window)

            def third_party():
                return next(r for r in page.findChildren(packs_page.PackRow) if r.dir.name == "third-party")

            def text():
                return " ".join(w.text() for w in third_party().findChildren(QLabel))
            n = len(gui.sft.read_pack(gui.sft.THIRD_PARTY)[1])                     # (however many it has)
            self.assertIn(f"▸ {n} tweaks", text())
            self.assertNotIn("Recline", text())
            QTest.mouseClick(third_party(), gui.Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
            self.assertIn(f"▾ {n} tweaks", text())
            self.assertIn("href='tweak:recline'>Recline</a> 🧪 🔗 — Use VR lying down", text())
            self.assertIn("✔ installed", text().split("tweak:recline")[1])
            self.assertNotIn("✔ installed", text().split("tweak:recline")[0])   # (the others aren't)
            page.open_link("tweak:recline")
            comp, = window.show_details.call_args[0]
            self.assertEqual(comp["id"], "recline")
            self.assertEqual(window.show_details.call_args[1]["back"], window.show_packs)
            QTest.mouseClick(third_party(), gui.Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
            self.assertIn(f"▸ {n} tweaks", text())

    def test_back_goes_where_the_page_came_from(self):
        w = gui.Window.__new__(gui.Window)
        w.close_details, back = mock.Mock(), mock.Mock()
        w.details_back = back
        w.leave_details()
        w.close_details.assert_called_once()
        back.assert_called_once()
        w.details_back = None
        w.leave_details()                                           # (the list: nothing more)
        back.assert_called_once()


class LinkedProject(unittest.TestCase):
    """A linked project (manifest link:): its page says it's linked and links its README; its status
    comes from lib/link.sh."""
    def test_page_and_status(self):
        import shutil
        from PyQt6.QtWidgets import QApplication, QLabel
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            t = d / "packs/mine/linked"
            t.mkdir(parents=True)
            readme = (ROOT / "examples/hello-pack/hello-frame/README.md").read_text()
            readme = readme.replace("\n---\n", "\nlink:\n  install: echo installing\n  installed: ~/linked-project\n"
                                    "  readme: https://example.org/linked#readme\n---\n", 1)
            (t / "README.md").write_text(readme)
            with mock.patch.object(gui.sft, "USER_PACKS", d / "packs"), mock.patch.object(gui.sft, "CONF", d), \
                    mock.patch.object(gui.sft, "TRUSTED", d / "trusted"), mock.patch.dict(os.environ, {"FRAME_TWEAKS_PACKS": ""}):
                gui.sft.set_trusted(d / "packs/mine", True)
                comp = next(c for c in gui.sft.load(refresh=True)["components"] if c["id"] == "linked")
                page = gui.Details(mock.Mock(), comp, (1, "not installed"))
                text = " ".join(w.text() for w in page.findChildren(QLabel))
                self.assertIn("🔗 Linked", text)
                self.assertIn("https://example.org/linked#readme", text)
                self.assertEqual(gui.sft.script(comp, "status")[2:], ["status", "linked"])
        gui.sft.load(refresh=True)


class SudoTag(unittest.TestCase):
    """A tweak whose install asks for the sudo password (manifest sudo:) says so on its page; a
    Homebrew one only while Homebrew isn't installed."""
    def test_page_says_why(self):
        from PyQt6.QtWidgets import QApplication, QLabel
        self.app = QApplication.instance() or QApplication([])

        def page_text(cid):
            page = gui.Details(mock.Mock(), gui.component(cid), (1, "not installed"))
            return " ".join(w.text() for w in page.findChildren(QLabel))
        self.assertIn("Asks for sudo", page_text("charge-limit"))
        self.assertIn("udev rule", page_text("charge-limit"))
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(gui.sft, "BREW", Path(d) / "brew"):            # no Homebrew yet
                self.assertIn("/home/linuxbrew", page_text("snip"))
            (Path(d) / "brew").touch()
            with mock.patch.object(gui.sft, "BREW", Path(d) / "brew"):            # Homebrew there: no tag
                self.assertNotIn("Asks for sudo", page_text("snip"))
        self.assertNotIn("Asks for sudo", page_text("cursor"))


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
        """One choice for the tweaks (keeping third-party apps by default), settings apart."""
        from PyQt6.QtWidgets import QApplication, QCheckBox, QPushButton, QRadioButton
        self.app = QApplication.instance() or QApplication([])
        window = mock.Mock()
        page = gui.Preferences(window)
        buttons = {b.text(): b for b in page.findChildren(QPushButton)}
        radios = {b.text(): b for b in page.findChildren(QRadioButton)}
        boxes = {b.text(): b for b in page.findChildren(QCheckBox)}
        self.assertEqual(list(radios), ["Uninstall the tweaks, but keep third-party apps",
                                        "Uninstall every tweak, third-party apps too", "Leave every tweak installed"])
        self.assertTrue(radios["Uninstall the tweaks, but keep third-party apps"].isChecked())   # (the safe one)
        for text, keep_tweaks, keep_apps, says in (
                ("Uninstall the tweaks, but keep third-party apps", False, True, "third-party apps stay"),
                ("Uninstall every tweak, third-party apps too", False, False, "third-party apps too"),
                ("Leave every tweak installed", True, True, "The tweaks stay installed.")):
            radios[text].setChecked(True)
            boxes["Also delete the settings"].setChecked(True)
            buttons["Uninstall Frame Tweaks…"].click()
            self.assertIn(says, page.leaving.text.text())
            self.assertIn("Settings are deleted.", page.leaving.text.text())
            window.uninstall_self.reset_mock()
            page.leaving.yes.click()
            window.uninstall_self.assert_called_once_with(keep_tweaks=keep_tweaks, settings="remove", keep_apps=keep_apps)

    def test_explanations_are_plain_text(self):
        """(they were escaped as HTML and shown as plain text: "they&#x27;re")"""
        from PyQt6.QtWidgets import QApplication, QLabel
        self.app = QApplication.instance() or QApplication([])
        page = gui.Preferences(mock.Mock())
        texts = [label.text() for label in page.findChildren(QLabel)]
        self.assertFalse([t for t in texts if "&#" in t or "&amp;" in t])
        self.assertTrue(any("Claude Code's ~/.claude" in t for t in texts))

    def test_uninstall_comes_last_below_a_line(self):
        from PyQt6.QtWidgets import QApplication, QFrame, QLabel
        self.app = QApplication.instance() or QApplication([])
        page = gui.Preferences(mock.Mock())
        headings = [w.text() for w in page.findChildren(QLabel) if w.objectName() == "name"]
        self.assertEqual(headings, ["Language", "This window", "Updates", "Uninstalling a tweak", "Uninstalling Frame Tweaks"])
        self.assertEqual(len([f for f in page.findChildren(QFrame) if f.objectName() == "separator"]), 1)

    def test_test_releases(self):
        """Get test releases too: the channel ./install.sh reads. Unticked on a test release, it asks:
        stay on it, or go back to the newest stable release now (an update --to stable)."""
        from PyQt6.QtWidgets import QApplication, QCheckBox, QPushButton
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d, mock.patch.object(gui.sft, "CHANNEL", Path(d) / "channel"), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_CHANNEL": ""}):
            window = mock.Mock()
            for version, asks in (("0.6.3", False), ("0.6.4-rc.1", True)):
                with mock.patch.object(gui.sft, "current_release", return_value=version):
                    page = gui.Preferences(window)
                    box = next(b for b in page.findChildren(QCheckBox) if b.text() == "Get test releases too")
                    self.assertFalse(box.isChecked())
                    box.setChecked(True)
                    self.assertEqual((Path(d) / "channel").read_text(), "beta\n")
                    window.channel_changed.assert_called()
                    box.setChecked(False)
                    self.assertEqual((Path(d) / "channel").read_text(), "stable\n")
                    self.assertEqual(page.going_back.isVisibleTo(page), asks, version)
            self.assertIn("You're on 0.6.4-rc.1, a test release.", page.going_back.text.text())
            buttons = {b.text(): b for b in page.going_back.findChildren(QPushButton)}
            buttons["Go back now"].click()
            window.run_update.assert_called_once_with(None, to="stable")
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}), contextlib.redirect_stdout(out):
            gui.Window.run_update(mock.Mock(), None, to="stable")
        self.assertEqual(out.getvalue(), "would run: ./install.sh update --to stable\n")

    def test_window_runs_uninstall_self_as_planned(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}), contextlib.redirect_stdout(out):
            gui.Window.uninstall_self(mock.Mock(), keep_tweaks=False, settings="keep")
            gui.Window.uninstall_self(mock.Mock(), keep_tweaks=False, settings="keep", keep_apps=False)
        self.assertEqual(out.getvalue().split("\n")[:2], ["would run: ./install.sh uninstall-self --keep-settings",
                                                           "would run: ./install.sh uninstall-self --remove-apps --keep-settings"])



class ContributeRow(unittest.TestCase):
    """The list ends with a row that isn't a tweak, under every group: how to help. (Built on a
    stand-in window: the real one would start SteamVR's button handling and the update check.)"""
    def test_row_and_page(self):
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget
        self.app = QApplication.instance() or QApplication([])
        holder = QWidget()
        window = mock.Mock(row_widgets=[], grid=QVBoxLayout(holder))
        gui.Window.add_contribute_row(window)
        self.assertEqual(len(window.row_widgets), 1)
        row = window.row_widgets[0]
        self.assertIsInstance(row, gui.ContributeRow)
        self.assertNotIn("_contribute", [c["id"] for c in gui.sft.components()])     # (not a tweak)
        self.assertEqual([b.text() for b in row.findChildren(QPushButton)], ["Get involved"])   # (no tick, ↻ or Hide)
        self.assertIn("Help make Frame Tweaks better", [w.text() for w in row.findChildren(QLabel)])
        self.assertFalse(any("Not a tweak" in w.text() for w in row.findChildren(QLabel)))
        row.findChildren(QPushButton)[0].click()
        window.show_contribute.assert_called_once()
        page = gui.ReadmePage(mock.Mock(), gui.REPO / "docs/contribute.md", "Help make Frame Tweaks better")
        text = page.findChildren(QTextBrowser)[0].toPlainText()
        for part in ("Suggest a third-party app", "tweak nobody has written yet", "Report a bug",
                     "Review a translation", "Add a language"):
            self.assertIn(part, text)
        holder.deleteLater()


class ShowTweak(unittest.TestCase):
    def test_opens_that_tweaks_page(self):
        """--show ID (lib/needs.py: "Open Frame Tweaks" for a feature whose tweak isn't installed)."""
        window = mock.Mock(rows=[{"id": "dictation"}, {"id": "speech"}])
        gui.Window.show_tweak(window, "speech")
        window.show_details.assert_called_once_with({"id": "speech"})
        gui.Window.show_tweak(window, "no-such-tweak")                   # (from a pack not in use: nothing)
        window.show_details.assert_called_once()



class ControllerButtonsOff(unittest.TestCase):
    """Controller buttons in VR are off until they work (docs/roadmap.md): no ⚙ option, and the
    window doesn't claim the buttons; its haptic ticks still work."""
    def test_no_option(self):
        from PyQt6.QtWidgets import QApplication, QCheckBox
        self.app = QApplication.instance() or QApplication([])
        self.assertFalse(gui.CONTROLLER_BUTTONS)
        texts = [b.text() for b in gui.Preferences(mock.Mock()).findChildren(QCheckBox)]
        self.assertNotIn("Controller buttons in VR", texts)
        self.assertNotIn("controller", gui.window_prefs())

    def test_haptics_without_claiming_buttons(self):
        fake = mock.MagicMock(k_unTrackedDeviceIndexInvalid=-1)
        fake.VROverlay.return_value.getPrimaryDashboardDevice.return_value = 2
        sys.path.insert(0, str(gui.REPO / "gui"))
        import vrbuttons
        with mock.patch.dict(sys.modules, {"openvr": fake}):
            b = vrbuttons.VRButtons({})
        self.assertTrue(b.started)
        self.assertFalse(b.ok)
        fake.VRInput.assert_not_called()                             # (no action manifest, no action set)
        b.poll(True)                                                 # (laser on the window: nothing claimed)
        b.haptic("press")
        fake.VRSystem.return_value.triggerHapticPulse.assert_called_once_with(2, 0, 3999)


if __name__ == "__main__":
    unittest.main()
