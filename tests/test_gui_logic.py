"""Pure logic of the installer window (no window is opened). Run: python3 -m unittest -v"""
import contextlib
import io
import os
import shutil
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
            with mock.patch.object(gui.sft, "build_version", return_value=now), \
                    mock.patch.object(gui.sft, "unfinished_update", return_value=[]):    # (not this Frame's records)
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
        w.rows = gui.components()                               # (the packs read again: the same tweaks)
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

    def test_an_exit_code_status_sh_doesnt_give(self):
        """status.sh ending some other way (127: a command missing, under set -e) is a warning,
        installed as ./install.sh counts it: it said "not installed" while the row was ticked."""
        self.assertEqual(gui.status_text((127, "")), ("! status check failed (exit 127)", "warn"))
        self.assertNotIn(127, gui.GONE)

    def test_a_tweak_gone_since_the_list_was_read(self):
        """Its pack turned off or changed, its folder moved (by an update): its status is "not
        available any more", not installed, and it has no update check. (Both raised TypeError,
        which showed the error page and left the row "checking…".)"""
        self.assertEqual(gui.status("no-such-tweak"), (gui.UNAVAILABLE, "not available any more"))
        self.assertIsNone(gui.update_check("no-such-tweak"))
        with tempfile.TemporaryDirectory() as d:
            moved = dict(gui.component("clipboard"), dir=Path(d) / "gone")
            with mock.patch.object(gui, "component", return_value=moved):
                self.assertEqual(gui.status("clipboard"), (gui.UNAVAILABLE, "not available any more"))
                self.assertIsNone(gui.update_check("clipboard"))
        self.assertIn(gui.UNAVAILABLE, gui.GONE)
        self.assertEqual(gui.status_text((gui.UNAVAILABLE, "not available any more")),
                         ("· not available any more", "missing"))

    def test_restart_line(self):
        """status.sh's "restart" line is a status of its own: installed (exit 2) or uninstalled (exit 1);
        other lines keep their code."""
        for out, code, want in (("restart  Load it\n", 2, (gui.RESTART, "Load it")), ("warning  Hmm\n", 2, (2, "Hmm")),
                                ("restart  Unload it\n", 1, (gui.UNLOAD, "Unload it")), ("missing  No\n", 1, (1, "No")),
                                ("ok       Fine\n", 0, (0, "Fine")), ("restart  x\n", 0, (0, "x"))):
            done = subprocess.CompletedProcess([], code, stdout=out, stderr="")
            with mock.patch.object(gui.subprocess, "run", return_value=done):
                self.assertEqual(gui.status("adb-scrcpy"), want, out)

    def test_a_check_that_fails_isnt_not_installed(self):
        """Exit 1 without "missing" or "restart" (a command in status.sh failed): installed by Frame
        Tweaks (its record), it's "status check failed", with what the check said last; without a
        record, not installed, as before. Another exit code (3 was RESTART, 4 UNLOAD): the same,
        record or not. (./install.sh status_of has the same rule.)"""
        for code, out, err, record, want in (
                (1, "", "cat: x: No such file\n\n", True, (2, "status check failed: cat: x: No such file")),
                (1, "", "", True, (2, "status check failed")),
                (1, "", "boom\n", False, (1, "")),
                (1, "missing  No\n", "", True, (1, "No")),
                (1, "restart  Unload it\n", "", True, (gui.UNLOAD, "Unload it")),
                (127, "", "\x1b[1;33mwarning:\x1b[0m x\nphone: command not found\n", False,
                 (2, "status check failed: phone: command not found")),
                (3, "", "", False, (2, "status check failed")),
                (4, "", "", False, (2, "status check failed"))):
            done = subprocess.CompletedProcess([], code, stdout=out, stderr=err)
            with mock.patch.object(gui.subprocess, "run", return_value=done), \
                    mock.patch.object(gui.sft, "installed_record", return_value=record):
                self.assertEqual(gui.status("adb-scrcpy"), want, (code, out, err, record))

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
            self.assertEqual(gui.sft.read_set(f), {"Privacy & security", "System"})
        self.assertEqual(gui.sft.read_set(Path("/nonexistent/x")), set())

    def test_latest_release_offline(self):
        with mock.patch.object(gui.urllib.request, "urlopen", side_effect=OSError("offline")):
            self.assertIsNone(gui.latest_release("https://example.invalid"))


def collecting_window(**attrs):
    """A Window with only what collect() looks at, none of its widgets: no row is shown, so only
    what it knows changes."""
    w = gui.Window.__new__(gui.Window)
    w.latest_futures, w.update_futures, w.futures, w.self_update, w.pack_check = {}, {}, {}, None, None
    w.state, w.updates, w.status_labels, w.details = {}, {}, {}, None
    w.pool, w.update_apply, w.fit_list = mock.Mock(), mock.Mock(), mock.Mock()
    for k, v in attrs.items():
        setattr(w, k, v)
    return w


def finished(result=None, error=None):
    from concurrent.futures import Future
    f = Future()
    if error is not None:
        f.set_exception(error)
    else:
        f.set_result(result)
    return f


class Collect(unittest.TestCase):
    """What the window does with its background checks' results (collect)."""
    def test_a_check_that_failed_is_said_on_its_row(self):
        """A status check that raised is a warning on its row: not "checking…" for good and the
        error page; the other rows' results come in too."""
        w = collecting_window()
        w.futures = {"a": finished(error=TypeError("'NoneType' object is not subscriptable")),
                     "clipboard": finished((0, "running"))}
        w.collect()
        self.assertEqual(w.state, {"a": (2, "status check failed: 'NoneType' object is not subscriptable"),
                                   "clipboard": (0, "running")})
        self.assertEqual(w.futures, {})

    def test_a_row_sft_no_longer_has(self):
        """(collect looked for its update-check.sh through sft's tweak, None by then: TypeError)"""
        w = collecting_window()
        w.futures = {"gone-tweak": finished((0, "fine"))}
        w.collect()
        self.assertEqual(w.state, {"gone-tweak": (0, "fine")})
        w.pool.submit.assert_not_called()

    def test_checks_cancelled_as_the_window_closes(self):
        """Closing cancels the checks still waiting: collect leaves them (it raised CancelledError
        for each, into window.log). (Closing stops it too: test_gui_window.py.)"""
        from concurrent.futures import Future
        cancelled = Future()
        cancelled.cancel()
        w = collecting_window(futures={"a": cancelled}, update_futures={"b": cancelled},
                              latest_futures={"c": cancelled}, self_update=cancelled, latest={}, update_state="check")
        w.collect()
        self.assertEqual((w.state, w.updates, w.latest, w.futures, w.self_update), ({}, {}, {}, {}, None))

    def test_refresh_drops_the_last_rounds_checks(self):
        """Refresh (or terminals closing one after another) while the last round's checks still wait
        for a worker: they're dropped, not run as well. (Three refreshes ran 75 status scripts.)"""
        import threading
        from concurrent.futures import ThreadPoolExecutor
        gate, runs = threading.Event(), []

        def slow(cid):
            runs.append(cid)
            gate.wait(5)
            return 1, ""
        pool = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(pool.shutdown, cancel_futures=True)
        w = gui.Window.__new__(gui.Window)
        w.rows, w.futures, w.pool = [{"id": i} for i in ("a", "b", "c")], {}, pool
        w.collecting, w.rebuild = mock.Mock(), mock.Mock()
        with mock.patch.object(gui, "status", slow):
            w.refresh()
            first = dict(w.futures)
            for _ in range(250):                       # (the worker took a's)
                if runs:
                    break
                time.sleep(0.02)
            w.refresh()
            gate.set()
            for f in w.futures.values():
                f.result(timeout=5)
        self.assertTrue(first["b"].cancelled() and first["c"].cancelled())
        self.assertEqual(sorted(runs), ["a", "a", "b", "c"])

    def test_an_update_found_goes_when_its_not_there(self):
        """↑ X available · Update goes once the check finds nothing newer, once the tweak isn't
        installed (its link installed it again), and once ↻ or Apply has run."""
        w = collecting_window(state={"full-keyboard": (0, "installed")})
        w.update_futures = {"full-keyboard": finished(("1.0.0", "1.1.0"))}
        w.collect()
        self.assertEqual(w.updates, {"full-keyboard": ("1.0.0", "1.1.0")})
        w.update_futures = {"full-keyboard": finished(None)}               # (the app updated itself)
        w.collect()
        self.assertEqual(w.updates, {})
        w.updates = {"full-keyboard": ("1.0.0", "1.1.0")}
        w.futures = {"full-keyboard": finished((1, "not installed"))}      # (unticked and applied)
        w.collect()
        self.assertEqual(w.updates, {})
        w.update_futures = {"full-keyboard": finished(("1.0.0", "1.1.0"))}   # (a check from before it went)
        w.collect()
        self.assertEqual(w.updates, {})
        w.updates, w.refresh = {"full-keyboard": ("1.0.0", "1.1.0"), "arrowpad": ("1", "2")}, mock.Mock()
        w.changed(["full-keyboard"])                                         # (↻ or Apply's terminal closed)
        self.assertEqual(w.updates, {"arrowpad": ("1", "2")})
        w.refresh.assert_called_once()
        w.changed, w.wanted = mock.Mock(), {"arrowpad": True}
        with mock.patch.object(gui, "QProcess") as qprocess, mock.patch.object(gui, "in_terminal"), \
                mock.patch.dict(os.environ):
            os.environ.pop("FRAME_TWEAKS_DRY_RUN", None)
            w.run_reinstall("full-keyboard")
            qprocess.return_value.finished.connect.call_args[0][0]()        # (its terminal closed)
            w.changed.assert_called_with(["full-keyboard"])
            w.run_changes(["arrowpad"], ["snip"])
            qprocess.return_value.finished.connect.call_args[0][0]()
            w.changed.assert_called_with(["arrowpad", "snip"])
        self.assertEqual(w.wanted, {})

    def test_a_tweaks_page_shows_its_status_as_it_comes(self):
        """(it said "checking…" until it was opened again)"""
        from PyQt6.QtWidgets import QApplication, QLabel
        self.app = QApplication.instance() or QApplication([])
        page = gui.Details(mock.Mock(latest={}), gui.component("clipboard"), None)
        status = lambda: next(w.text() for w in page.findChildren(QLabel) if "<b>Status</b>" in w.text())
        self.assertIn("checking…", status())
        w = collecting_window(details=page)
        w.futures = {"arrowpad": finished((2, "needs a look"))}                 # (another tweak's)
        w.collect()
        self.assertIn("checking…", status())
        w.futures = {"clipboard": finished((0, "running"))}                    # (its row isn't shown: hidden, say)
        w.collect()
        self.assertIn("✔ running", status())
        self.assertNotIn("checking…", status())


class Reload(unittest.TestCase):
    """The list follows the tweaks sft read: as packs change under the window, or its language."""
    def test_the_list_follows_the_packs(self):
        """When sft read the packs again (opening Packs, Check for updates, a pack's update) and
        they're not the list's any more, the list is read again: its rows asked sft for tweaks it no
        longer had."""
        w = gui.Window.__new__(gui.Window)
        w.use_tweaks, w.rows = mock.Mock(), gui.components()
        w.follow_packs()
        w.use_tweaks.assert_not_called()
        w.rows = gui.components()[:-1]                  # (one more since: a pack trusted outside the window)
        w.follow_packs()
        w.use_tweaks.assert_called_once()
        w.rows = [dict(c, dir=Path("/elsewhere") / c["id"]) for c in gui.components()]   # (moved by an update)
        w.follow_packs()
        self.assertEqual(w.use_tweaks.call_count, 2)

    def test_a_known_issue_a_pack_brings(self):
        """Its newer release is looked for (only when the window opened, before: "Checking…" for
        good on its page), once."""
        w = gui.Window.__new__(gui.Window)
        w.pool, w.latest, w.latest_futures, w.refresh, w.collecting = mock.Mock(), {}, {}, mock.Mock(), mock.Mock()
        issue = {"version": "1.0", "short": "s", "long": "l", "latest": "https://api.github.com/repos/o/r/releases/latest"}
        rows = gui.components() + [dict(gui.component("clipboard"), id="x-issue", known_issue=issue, settings=None)]
        with mock.patch.object(gui, "components", return_value=rows), mock.patch.object(gui.sft, "load"), \
                mock.patch.object(gui.sft, "settings_specs", return_value={}), mock.patch.object(gui.sft, "SETTINGS", {}), \
                mock.patch.dict(gui.SETTINGS_PAGES), mock.patch.object(gui, "KNOWN_ISSUES", {}):
            w.reload_tweaks()
            self.assertIn(mock.call(gui.latest_release, issue["latest"]), w.pool.submit.call_args_list)
            self.assertIn("x-issue", w.latest_futures)
            w.pool.submit.reset_mock()
            w.reload_tweaks()
        w.pool.submit.assert_not_called()

    def test_why_its_not_needed_follows_the_language(self):
        """(a tweak's needed.sh says why in the window's language: it stayed in the one it opened in)"""
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(gui.sft._NOT_NEEDED):     # (what's known, kept)
            (Path(d) / "needed.sh").write_text('echo "not here: $FRAME_TWEAKS_LANG_RESOLVED"; exit 1\n')
            row = dict(gui.component("clipboard"), id="x-needs", dir=Path(d), known_issue=None)
            with mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANG_RESOLVED": "en"}):
                self.assertEqual(gui.sft.not_needed([row], refresh=True), {"x-needs": "not here: en"})
            w = gui.Window.__new__(gui.Window)
            w.show_hidden, w.build_ui, w.refresh, w.update_newest = mock.Mock(), mock.Mock(), mock.Mock(), None
            with mock.patch.dict(os.environ, {"FRAME_TWEAKS_LANG_RESOLVED": "es_419"}), \
                    mock.patch.object(gui, "components", return_value=[row]), mock.patch.object(gui.sft, "load"), \
                    mock.patch.object(gui.sft, "settings_specs", return_value={}), mock.patch.object(gui.sft, "SETTINGS", {}), \
                    mock.patch.object(gui, "KNOWN_ISSUES", {}):
                w.retranslate()
                self.assertEqual(gui.sft.not_needed([row]), {"x-needs": "not here: es_419"})


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

    def test_run_where_the_tweak_is_now(self):
        """Run starts the tweak where sft has it now, not where its row was read (an update moved its
        folder: TypeError); gone altogether, it says so."""
        comp = next(c for c in gui.components() if gui.run_label(c["id"]) and (c["dir"] / "run.sh").is_file()
                    and c["id"] not in gui.PAGES)
        w = gui.Window.__new__(gui.Window)
        w.state, w.say = {}, mock.Mock()
        stale = dict(comp, dir=Path("/nonexistent/moved") / comp["id"])
        with mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}), contextlib.redirect_stdout(io.StringIO()) as out:
            w.run(stale)
            self.assertEqual(out.getvalue(), f"would run: bash {comp['dir'] / 'run.sh'}\n")
            with mock.patch.object(gui, "component", return_value=stale):
                w.run(stale)
        self.assertIn("Close and reopen Frame Tweaks", w.say.call_args[0][0])
        self.assertEqual(out.getvalue().count("would run"), 1)

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
        # With the VR session's runtime folder and D-Bus, wherever the window is: from desktop
        # mode, steamvr restart couldn't reach the user service manager.
        with mock.patch.object(gui, "QProcess") as qprocess, mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "",
                                                                                         "XDG_RUNTIME_DIR": "/run/user/1/nested"}):
            w.do_restart_steamvr()
        program, args = qprocess.startDetached.call_args[0]
        self.assertEqual((program, args[-2:]), ("env", ["steamvr", "restart"]))
        self.assertIn(f"XDG_RUNTIME_DIR=/run/user/{os.getuid()}", args)
        self.assertIn(f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{os.getuid()}/bus", args)
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
            self.assertEqual(section.notice.text(), "Done")       # (the page opened again: not "Working…" for good)

    def test_a_page_opened_again_says_how_it_goes(self):
        """Opened again while its action runs, a settings page says so, its button dimmed, and how
        it went at the end; another action meanwhile waits for it."""
        from PyQt6.QtWidgets import QApplication, QWidget
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "act.sh").write_text(f"sleep 0.5; touch {d}/done; echo Charging to 100% once\n")
            (d / "other.sh").write_text(f"touch {d}/other\n")
            act = {"label": "Charge to 100% once", "script": "act.sh", "dir": d}
            spec = {"file": d / "x.json", "format": "json", "about": "", "note": "", "options": [],
                    "actions": [act], "checkboxes": set(), "swatches": set(), "include": []}

            class Window(QWidget):
                def go_back(self):
                    pass
            window = Window()
            self.addCleanup(window.deleteLater)
            self.addCleanup(lambda: [p.kill() or p.waitForFinished(3000) for p in window.findChildren(gui.QProcess)])
            with mock.patch.dict(gui.sft.SETTINGS, {"x-test": spec}), mock.patch.dict(os.environ):
                os.environ.pop("FRAME_TWEAKS_DRY_RUN", None)
                first = gui.SettingsPage(window, "x-test")
                first.setParent(window)
                first.sections[0].actions[0][1].click()
                first.deleteLater()                                     # ← Back
                again = gui.SettingsPage(window, "x-test")
                again.setParent(window)
                button = again.sections[0].actions[0][1]
                self.assertEqual(again.notice.text(), "Working… (a download can take a minute)")
                self.assertFalse(button.isEnabled())
                again.sections[0].act({"script": "other.sh", "dir": d})
                self.assertEqual(again.notice.text(), "Another action is still running: try again once it's done.")
                for _ in range(200):
                    self.app.processEvents()
                    if (d / "done").exists() and gui.running_action(window) is None:
                        break
                    time.sleep(0.05)
                self.app.processEvents()
                self.assertEqual(again.notice.text(), "Charging to 100% once")
                self.assertTrue(button.isEnabled())
                self.assertFalse((d / "other").exists())

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

    def test_the_pop_up_after_a_link_is_twice_a_tooltip(self):
        """The owner's ask: the pop-up by the pointer ("Link copied", "Opening in Firefox…") twice a
        tooltip's size and twice as long (Qt's: small, and gone too soon in VR)."""
        from PyQt6.QtWidgets import QApplication, QToolTip
        self.app = QApplication.instance() or QApplication([])
        with mock.patch.object(gui.link_tip.QToolTip, "showText") as shown:
            gui.follow_link("copy:https://example.com/x")
        _pos, text, _w, _rect, msecs = shown.call_args[0]
        self.assertIn("Link copied", text)
        size = QToolTip.font().pointSizeF()
        self.assertIn(f"font-size:{size * 2:g}pt" if size > 0 else "px", text)
        self.assertEqual(msecs, 2 * gui.link_tip.qt_time("Link copied"))
        self.assertEqual(msecs, 20000)

    def test_a_link_opens_when_browser_py_trips(self):
        """lib/browser.py raising (over a desktop entry it can't read, say) opened no link at all:
        the link opens the usual way instead, and its log says why."""
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        gone = FileNotFoundError(2, "No such file or directory", "/x/applications/gone.desktop")
        for url, how in (("https://example.com/a", "launch"), ("file:///tmp/a.md", "open_path")):
            with mock.patch.object(gui.browser, how, side_effect=gone), mock.patch.object(gui.browser, "log") as log, \
                    mock.patch.object(gui, "QDesktopServices") as desktop:
                gui.follow_link(url)
            desktop.openUrl.assert_called_once_with(gui.QUrl(url))
            self.assertIn("FileNotFoundError", log.call_args[0][0])

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
                window.details = page
                buttons = lambda: {b.text(): b for b in page.findChildren(QPushButton) if b.isVisibleTo(page)}

                def wait():
                    for _i in range(300):
                        QApplication.processEvents()
                        gui.Window.finish_pack_job(window)          # (the window's collect finishes it)
                        if not page.busy():
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
                gui.sft.set_trusted(d / "packs/their-pack", True)             # (only a trusted pack updates)
                window.pack_updates = {(d / "packs/their-pack").resolve()}     # (Check for updates found one)
                page.build()
                self.assertTrue(any("A newer version is out" in w.text() for w in page.findChildren(QLabel)))
                buttons()["Update"].click()
                wait()
                self.assertEqual(page.notice.text(), "Hello pack is up to date.")
                self.assertEqual(window.pack_updates, set())                     # (got it: the notice goes)
                window.show_pack_updates.assert_called()
                window.pack_updates = {(d / "packs/their-pack").resolve()}     # (found newer again)
                window.show_pack_updates.reset_mock()
                buttons()["Remove…"].click()
                buttons()["Yes, delete it"].click()
                self.assertEqual(page.notice.text(), "Removed Hello pack.")
                self.assertEqual(window.pack_updates, set())                     # (gone: its update too)
                window.show_pack_updates.assert_called()
                self.assertFalse((d / "packs/their-pack").exists())
                window.reload_tweaks.assert_called()
        gui.sft.load(refresh=True)



class PacksUnderTheWindow(unittest.TestCase):
    """The Packs page shows the packs as read when it opened (and by what its buttons change): its
    every click read them again, replacing sft's tweaks under the window's list. A pack update
    still running when you go Back is finished by the window, which says nothing but follows it."""
    def test_a_click_doesnt_read_them_again(self):
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        page = gui.Packs(mock.Mock())
        with mock.patch.object(gui.sft, "load", wraps=gui.sft.load) as load:
            page.toggle_inventory(gui.sft.THIRD_PARTY)
            page.confirm(gui.sft.THIRD_PARTY)
        self.assertTrue(load.called)
        self.assertFalse([c for c in load.call_args_list if c.kwargs.get("refresh")])

    def test_an_update_that_ends_after_back(self):
        import threading
        from PyQt6.QtCore import QCoreApplication, QEvent
        from PyQt6.QtWidgets import QApplication, QPushButton
        self.app = QApplication.instance() or QApplication([])
        gate = threading.Event()
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            shutil.copytree(ROOT / "examples/hello-pack", d / "packs" / "mine")
            mine = (d / "packs" / "mine").resolve()

            def update_pack(folder):                    # (git pull brought a change)
                gate.wait(5)
                (mine / "hello-frame/README.md").write_text((mine / "hello-frame/README.md").read_text() + "\nNew.\n")
                gui.sft.load(refresh=True)
                return {"files": ["hello-frame/README.md"], "log": ["a change"]}
            origin = lambda folder: "https://example.org/mine.git" if Path(folder) == mine else None   # (added from a link)
            with mock.patch.multiple(gui.sft, USER_PACKS=d / "packs", CONF=d, TRUSTED=d / "trusted",
                                     pack_origin=origin, update_pack=update_pack), \
                    mock.patch.dict(os.environ, {"FRAME_TWEAKS_PACKS": ""}):
                gui.sft.set_trusted(mine, True)
                window = mock.Mock(details=None, pack_job=None, pack_updates={mine})
                page = gui.Packs(window)
                window.details = page
                next(b for b in page.findChildren(QPushButton) if b.text() == "Update").click()
                self.assertTrue(page.busy())
                window.details = None                   # ← Back
                page.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                again = gui.Packs(window)                # (and Packs again, while it runs)
                self.assertEqual(again.notice.text(), "Updating Hello pack…")
                self.assertFalse(again.add_button.isEnabled())
                again.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                gate.set()
                for _ in range(250):
                    gui.Window.finish_pack_job(window)        # (the window's collect)
                    if window.pack_job is None:
                        break
                    time.sleep(0.02)
                self.assertIsNone(window.pack_job)
                self.assertEqual(window.pack_updates, set())     # (got it: the window's notice goes)
                window.show_pack_updates.assert_called()
                window.follow_packs.assert_called_once()          # (its tweaks wait to be trusted again)
                self.assertNotIn("hello-frame", [c["id"] for c in gui.sft.components()])
        gui.sft.load(refresh=True)


class StuckWindow(unittest.TestCase):
    """A second launch that finds the open window stuck stops it, and only it: a Python running this
    very script. (It stopped anything whose command line named gui/frame-tweaks-gui.py: an editor
    with it open, say.)"""
    def test_only_the_window(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "gui").mkdir()
            script, other = d / "gui/frame-tweaks-gui.py", d / "other.py"
            for f in (script, other):
                f.write_text("import time\ntime.sleep(30)\n")
            ours = []

            def start(argv0, *args):                    # (a Python under another name, as exec -a gives it)
                p = subprocess.Popen(["bash", "-c", 'exec -a "$0" "$@"', argv0, sys.executable, *args], cwd=d)
                self.addCleanup(lambda: (p.poll() is None and p.kill(), p.wait()))
                ours.append(p.pid)
                for _ in range(100):                     # (until it shows its own command line)
                    if Path(f"/proc/{p.pid}/cmdline").read_bytes().startswith(argv0.encode()):
                        break
                    time.sleep(0.02)
                return p
            window = start(str(d / "venv/bin/sft-python"), str(script))
            from_repo = start(str(d / "venv/bin/python3"), "gui/frame-tweaks-gui.py")     # (as ./install.sh gives it)
            editor = start("kate", str(script))
            named = start("python3", str(other), str(script))
            signalled, real_kill = [], os.kill

            def kill(pid, sig):                         # (only ever these processes)
                signalled.append(pid)
                if pid in ours:
                    real_kill(pid, sig)
            with mock.patch.object(gui, "SCRIPT", script.resolve()), mock.patch.object(gui.os, "kill", kill), \
                    mock.patch.object(Path, "home", lambda: d):
                gui.stop_stuck_windows()
            for p in (window, from_repo):
                self.assertIsNotNone(p.wait(timeout=5))
            self.assertIsNone(editor.poll())
            self.assertIsNone(named.poll())
            self.assertEqual(set(signalled), {window.pid, from_repo.pid})
            self.assertIn("an open window didn't answer", (d / ".local/state/frame-tweaks/logs/window.log").read_text())


class HandOver(unittest.TestCase):
    """A second launch hands over to the open window, which answers with its session: open in
    the other one, a notification says where; no answer (stuck), it's stopped and this launch
    opens a window. (A plain socket server in a thread stands in for the open window.)"""
    def serve(self, answer):
        import socket
        import threading
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "server")
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(path)
        srv.listen(1)
        self.addCleanup(srv.close)
        self.got = []

        def run():
            conn, _ = srv.accept()
            if answer is not None:
                conn.sendall(answer.encode())
            self.got.append(conn.recv(100).decode())
            time.sleep(0.5)
            conn.close()
        self.server = threading.Thread(target=run, daemon=True)
        self.server.start()
        return path

    def hand_over(self, answer, session_env):
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        path = self.serve(answer)
        with mock.patch.object(gui, "SERVER", path), mock.patch.object(gui, "ANSWER_MS", 800), \
                mock.patch.object(gui, "notify") as notify, mock.patch.object(gui, "stop_stuck_windows") as stop, \
                mock.patch.dict(os.environ, session_env, clear=False):
            done = gui.hand_over("clipboard")
        self.server.join(5)                                    # (what it was sent: once it's read it)
        return done, notify, stop

    def test_open_in_the_other_session(self):
        done, notify, stop = self.hand_over("VR", {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0"})
        self.assertTrue(done)
        self.assertEqual(notify.call_args[0][0], "Frame Tweaks is already open in VR")
        stop.assert_not_called()
        self.assertEqual(self.got, ["show clipboard"])

    def test_open_in_this_session(self):
        done, notify, stop = self.hand_over("desktop mode", {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0"})
        self.assertTrue(done)
        notify.assert_not_called()

    def test_stuck(self):
        done, notify, stop = self.hand_over(None, {"XDG_CURRENT_DESKTOP": "KDE"})
        self.assertFalse(done)                                  # (this launch opens a window)
        stop.assert_called_once()

    def test_none_open(self):
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        with mock.patch.object(gui, "SERVER", os.path.join(tempfile.gettempdir(), "no-such-ft-server")), \
                mock.patch.object(gui, "stop_stuck_windows") as stop:
            self.assertFalse(gui.hand_over())
        stop.assert_not_called()


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


class NotNeeded(unittest.TestCase):
    """A tweak this Frame doesn't need (its needed.sh: exit 1, why) says so on its page."""
    def test_page_says_why(self):
        from PyQt6.QtWidgets import QApplication, QLabel
        self.app = QApplication.instance() or QApplication([])

        def page_text(cid):
            page = gui.Details(mock.Mock(), gui.component(cid), (1, "not installed"))
            return " ".join(w.text() for w in page.findChildren(QLabel))
        with mock.patch.object(gui.sft, "not_needed", lambda rows=None, refresh=False: {"cursor": "SteamOS does it"}):
            self.assertIn("This Frame doesn't need it: SteamOS does it", page_text("cursor"))
            self.assertNotIn("doesn't need it", page_text("charge-limit"))


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

    def test_the_look_of_installs_in_a_terminal(self):
        """⚙ Preferences → Installing in a terminal: the choice lands in the file lib/splash.py
        reads, and Show me runs its demo in a terminal."""
        from PyQt6.QtCore import QProcess
        from PyQt6.QtWidgets import QApplication, QPushButton
        import splash
        self.app = QApplication.instance() or QApplication([])
        env = {k: v for k, v in os.environ.items() if k != "FRAME_TWEAKS_DRY_RUN"}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(splash, "SETTING", Path(d) / "splash"), \
                mock.patch.dict(os.environ, {**env, "FRAME_TWEAKS_SPLASH": ""}, clear=True):
            page = gui.Preferences(mock.Mock())
            buttons = {b.text(): b for b in page.findChildren(QPushButton)}
            self.assertTrue(buttons["Animated"].isChecked())          # (the default)
            buttons["Output only"].click()
            self.assertEqual((Path(d) / "splash").read_text(), "off\n")
            self.assertEqual(splash.setting(), "off")
            self.assertFalse(buttons["Animated"].isChecked())
            buttons["Still"].click()
            self.assertEqual(splash.setting(), "still")
            with mock.patch.object(QProcess, "startDetached") as start:
                buttons["Show me"].click()
            program, args = start.call_args.args[:2]
            self.assertEqual(program, "konsole")
            self.assertIn("lib/splash.py --demo", args[-1])

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
        self.assertEqual(headings, ["Language", "This window", "Updates", "Installing in a terminal",
                                    "Uninstalling a tweak", "Uninstalling Frame Tweaks"])
        self.assertEqual(len([f for f in page.findChildren(QFrame) if f.objectName() == "separator"]), 1)

    def test_a_question_scrolls_into_view(self):
        """Uninstall Frame Tweaks… opens its question below the button, at the page's bottom: the page
        scrolls to show all of it (it was easy to miss)."""
        from PyQt6.QtCore import QPoint
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QApplication, QPushButton
        self.app = QApplication.instance() or QApplication([])
        page = gui.Preferences(mock.Mock())
        page.resize(900, 500)
        page.show()
        QTest.qWait(50)
        self.assertEqual(page.scroll.verticalScrollBar().value(), 0)
        next(b for b in page.findChildren(QPushButton) if b.text() == "Uninstall Frame Tweaks…").click()
        QTest.qWait(100)
        box, view = page.leaving, page.scroll.viewport()
        self.assertTrue(box.isVisible())
        top, bottom = box.mapTo(view, QPoint(0, 0)).y(), box.mapTo(view, QPoint(0, box.height())).y()
        self.assertGreater(page.scroll.verticalScrollBar().value(), 0)
        self.assertTrue(0 <= top and bottom <= view.height(), (top, bottom, view.height()))
        page.close()

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



class ReadmeShown(unittest.TestCase):
    """📖 README: all of it. Qt's Markdown reader drops the text after an HTML block it can't
    place, and a picture with a caption (<br><sub>…</sub>) was one: the page showed its first
    paragraph, then blank lines with only the inline code left."""
    def test_every_heading_and_the_text_after_a_captioned_picture(self):
        import re
        from PyQt6.QtWidgets import QApplication, QTextBrowser
        self.app = QApplication.instance() or QApplication([])
        page = gui.ReadmePage(mock.Mock())
        text = page.findChildren(QTextBrowser)[0].toPlainText()
        src = (gui.REPO / "README.md").read_text()
        for h in re.findall(r"^#{1,4} (.+)$", src, re.M):
            self.assertIn(re.sub(r"[`*]", "", h).strip(), text)
        self.assertIn("Typing is hard.", text)
        self.assertNotRegex(text, r"(\n[ \t]*){4,}")                 # (no runs of blank lines)
        self.assertNotRegex(text, r"</?(p|sub|br|img|details)\b")

    def test_a_captioned_picture(self):
        md = gui.plain_markdown('<p align="center"><img src="a.png" width="9" alt="A view"><br>\n'
                                '<sub>What it shows,\nin two lines.</sub></p>\n\nAfter.\n')
        self.assertEqual(md, "![A view](a.png)\n\n*What it shows, in two lines.*\n\nAfter.\n")

    def test_pictures_and_line_breaks_lose_nothing(self):
        """Every picture in a paragraph, its attributes in any order and quoted any way; one with no
        </p> ends where its HTML block does (a blank line), not at a later </p>; a <br> is a space;
        code is left as it is."""
        f = gui.plain_markdown
        self.assertEqual(f('<p align=center><img src=a.png alt=A><img src="b.png" alt="B"></p>\n'),
                         "![A](a.png) ![B](b.png)\n")
        self.assertEqual(f("<p><img alt='A' src='a.png'>\n\nAfter.\n\n<p>x</p>\n"), "![A](a.png)\n\nAfter.\n\n<p>x</p>\n")
        self.assertEqual(f("line one<br>line two"), "line one line two")
        for kept in ("Use `<br>` here.", "```\na<br>b <sub>c</sub>\n```\n", "```\n<p><img src=a.png></p>\n```\n"):
            self.assertEqual(f(kept), kept)


class EveryPageShown(unittest.TestCase):
    """Every Markdown page the window shows (each tweak's README in the packs in use, the README,
    docs/contribute.md), rendered as it shows it: its headings there, no runs of blank lines, no
    HTML in the text, and most of its words. Qt's Markdown reader drops the text after HTML it
    can't place: a captioned picture blanked the README, a "<country>" half of NordVPN's page."""
    def test_all_of_each(self):
        import re
        from PyQt6.QtWidgets import QApplication
        import manifest
        self.app = QApplication.instance() or QApplication([])
        pages = [(f, {"official": True, "id": None, "dir": gui.REPO}, f.read_text())
                 for f in (gui.REPO / "README.md", gui.REPO / "docs/contribute.md")]
        for c in gui.sft.components():
            body = manifest.front_matter(c["readme"].read_text())[1]
            pages.append((c["readme"], c, re.sub(r"<!-- generated:intro .*?<!-- /generated:intro -->\n*", "", body, flags=re.S)))
        for path, comp, src in pages:
            with self.subTest(page=str(path)):
                view = gui.readme_browser(src, comp)
                text = view.toPlainText()
                for h in re.findall(r"^#{1,4} (.+)$", re.sub(r"```.*?```", "", src, flags=re.S), re.M):
                    self.assertIn(re.sub(r"[`*\[\]]|\(.*?\)", "", h).strip(), text)
                self.assertNotRegex(text, r"(\n[ \t]*){4,}")
                self.assertNotRegex(text, r"</?(p|sub|br|img|details|summary)\b")
                words = len(re.sub(r"<[^>]+>|\(http[^)]*\)|[#*`>|\-]", "", src).split())
                self.assertGreater(len(text.split()), 0.8 * words)

    def test_a_placeholder_is_text(self):
        f = gui.literal_placeholders
        self.assertEqual(f('named "NordVPN <country>". After.'), 'named "NordVPN &lt;country&gt;". After.')
        for kept in ("Run `ssh <host>` here.", "```\nexample <id>\n```", "See <https://example.org> and <b>bold</b>.",
                     "    indented <code> line"):
            self.assertEqual(f(kept), kept)
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        view = gui.readme_browser("Named NordVPN <country>.\n\nThe rest is here.\n", {"official": True, "id": None, "dir": gui.REPO})
        self.assertIn("NordVPN <country>.", view.toPlainText())
        self.assertIn("The rest is here.", view.toPlainText())


class CodeInAList(unittest.TestCase):
    def test_an_indented_code_block_is_code(self):
        """A ``` block indented in a list item is code: its <ip> was taken for HTML in prose and shown
        as &lt;ip&gt;."""
        import manifest
        md = "1. Run this:\n\n   ```sh\n   adb pair <ip>:<port> <code>\n   ```\n\nThen <country>.\n"
        self.assertEqual(gui.literal_placeholders(md), md.replace("<country>", "&lt;country&gt;"))
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        c = gui.component("adb-scrcpy")
        text = gui.readme_browser(manifest.front_matter(c["readme"].read_text())[1], c).toPlainText()
        self.assertIn("adb pair <ip>:<pairing-port>", text)      # (the code is typed at adb's prompt)
        self.assertNotIn("&lt;", text)


class DetailsScroll(unittest.TestCase):
    """A tweak's page scrolls as one below its header (Back, the title): a long table of facts
    left the README a narrow strip to scroll in. The README is shown whole; a wheel over it, the
    keys that scroll, and a link to one of its headings, scroll the page; Ctrl+wheel doesn't (it
    zooms the README), and what's wider than it scrolls sideways in it."""
    def setUp(self):
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])

    def show(self, widget, width, height):
        widget.resize(width, height)
        widget.show()
        self.addCleanup(widget.deleteLater)
        self.addCleanup(widget.close)

    def wait_for(self, done):
        from PyQt6.QtTest import QTest
        for _ in range(100):                      # (fit runs once the layout has settled)
            if done():
                return
            QTest.qWait(20)

    def wheel(self, view, dy, mods=gui.Qt.KeyboardModifier.NoModifier):
        from PyQt6.QtCore import QPoint, QPointF
        from PyQt6.QtGui import QWheelEvent
        from PyQt6.QtWidgets import QApplication
        vp = view.viewport()
        at = QPointF(vp.width() / 2, 10)
        QApplication.sendEvent(vp, QWheelEvent(at, QPointF(vp.mapToGlobal(at.toPoint())), QPoint(0, 0), QPoint(0, dy),
                                               gui.Qt.MouseButton.NoButton, mods, gui.Qt.ScrollPhase.NoScrollPhase, False))

    def test_one_page(self):
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtWidgets import QApplication
        page = gui.Details(mock.Mock(latest={}), gui.component("charge-limit"), (1, "not installed"))
        self.show(page, 1000, 600)
        outer = page.scroll.verticalScrollBar()
        self.wait_for(lambda: outer.maximum() > 0)
        self.assertEqual(page.readme.verticalScrollBar().maximum(), 0)          # (shown whole)
        self.assertGreater(outer.maximum(), 0)
        self.wheel(page.readme, -240)
        self.assertGreater(outer.value(), 0)
        outer.setValue(0)
        self.wheel(page.readme, -240, gui.Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(outer.value(), 0)
        for key in (gui.Qt.Key.Key_PageDown, gui.Qt.Key.Key_End):
            outer.setValue(0)
            QApplication.sendEvent(page.readme, QKeyEvent(QKeyEvent.Type.KeyPress, key, gui.Qt.KeyboardModifier.NoModifier))
            self.assertGreater(outer.value(), 0, key)
        outer.setValue(0)
        gui.to_heading(page.readme, "how-it-works")
        self.assertGreater(outer.value(), 0)

    def test_ctrl_wheel_zooms(self):
        """Ctrl+wheel makes a README's text larger or smaller: the window's style sheet sets the
        font's size, so QTextEdit's own zoom did nothing. Shown whole, the README grows with it."""
        page = gui.Details(mock.Mock(latest={}), gui.component("charge-limit"), (1, "not installed"))
        page.setStyleSheet(gui.STYLE)                                   # (the window's)
        self.show(page, 1000, 600)
        view, outer = page.readme, page.scroll.verticalScrollBar()
        self.wait_for(lambda: outer.maximum() > 0)
        size, height = view.document().size().height(), view.height()
        self.wheel(view, 120, gui.Qt.KeyboardModifier.ControlModifier)
        self.wait_for(lambda: view.height() > height)
        self.assertGreater(view.document().size().height(), size)
        self.assertGreater(view.height(), height)
        self.assertEqual(outer.value(), 0)                              # (not scrolled)
        self.wheel(view, -360, gui.Qt.KeyboardModifier.ControlModifier)
        self.assertLess(view.document().size().height(), size)
        readme = gui.ReadmePage(mock.Mock())                            # (📖 README: not shown whole)
        readme.setStyleSheet(gui.STYLE)
        self.show(readme, 1000, 600)
        view = readme.findChild(gui.QTextBrowser)
        size = view.document().size().height()
        self.wheel(view, 120, gui.Qt.KeyboardModifier.ControlModifier)
        self.assertGreater(view.document().size().height(), size)

    def test_wider_than_the_page(self):
        from PyQt6.QtWidgets import QScrollArea
        view = gui.full_height(gui.readme_browser("Intro.\n\n![The window](docs/images/details.png)\n\nAfter.\n",
                                                  {"official": True, "id": None, "dir": gui.REPO}))
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(view)
        self.show(area, 400, 600)
        bar = view.horizontalScrollBar()
        self.wait_for(lambda: bar.maximum() > 0 and bar.isVisible())
        self.assertGreater(bar.maximum(), 0)
        self.assertTrue(bar.isVisible())
        self.assertEqual(view.verticalScrollBar().maximum(), 0)                 # (the bar hides none of it)


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
        for part in ("give it a star on GitHub", "Suggest a third-party app", "tweak nobody has written yet",
                     "Report a bug", "Review a translation", "Add a language"):
            self.assertIn(part, text)
        self.assertIn("https://github.com/AstronautCheetah/frame-tweaks", page.findChildren(QTextBrowser)[0].toHtml())
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
