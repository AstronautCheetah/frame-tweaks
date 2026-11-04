"""Wallet apps: the installer window's app lists, and wallet-launcher wrapping a system app."""
import contextlib
import io
import os
import sys
import shutil
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
from helpers import load_script, untipped_icon_buttons  # noqa: E402
gui = load_script(ROOT / "gui" / "frame-tweaks-gui.py", "gui")
import wallet_page as wp  # noqa: E402  (the window's Wallet apps page; gui put it on sys.path)
from PyQt6 import sip  # noqa: E402
wl = load_script(ROOT / "packs/core/wallet" / "wallet-launcher", "wl")


def entry(d, app_id, exec_line, **extra):
    d.mkdir(parents=True, exist_ok=True)
    lines = ["[Desktop Entry]", "Type=Application", f"Name={app_id.title()}", f"Exec={exec_line}"]
    lines += [f"{k}={v}" for k, v in extra.items()]
    (d / f"{app_id}.desktop").write_text("\n".join(lines) + "\n")


class Lists(unittest.TestCase):
    def setUp(self):
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        self.own, self.flat, self.sys, self.roots = t / "own", t / "flat", t / "sys", t / "roots"
        entry(self.flat, "org.notes", "flatpak run org.notes")
        (self.roots / "org.notes/current/active/files/notes").mkdir(parents=True)
        (self.roots / "org.notes/current/active/files/notes/resources.pak").touch()
        entry(self.flat, "org.editor", "flatpak run org.editor")
        entry(self.sys, "org.kde.dolphin", "dolphin %u")
        entry(self.sys, "hidden-helper", "helper", NoDisplay="true")
        entry(self.own, "Some Game", "steam steam://rungameid/123")
        entry(self.own, "mytool", "/opt/mytool/run")
        entry(self.own, "arrowpad", "/home/u/.local/bin/arrowpad --desktop")        # (Frame Tweaks' own)
        entry(self.own, "org.editor", "/home/u/.local/bin/frame-outer-bus flatpak run org.editor", **{"X-FrameTweaks-Wallet": "true"})
        self.patch = mock.patch.multiple(wp, LAUNCHERS=self.own, FLATPAK_APPS=[self.flat],
                                         SYSTEM_APPS=[self.sys], FLATPAK_ROOTS=[self.roots])
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_every_kind_of_installed_app_is_offered_once(self):
        protected = wp.protected_apps()
        self.assertEqual([a["id"] for a in protected], ["org.editor"])
        self.assertTrue(protected[0]["shared"])
        offered = {a["id"]: a["kind"] for a in wp.wallet_candidates({"org.editor"})}
        # Steam shortcuts, hidden entries and protected apps aren't offered.
        self.assertEqual(offered, {"org.notes": "Flatpak", "org.kde.dolphin": "System app", "mytool": "Your app",
                                   "arrowpad": "Frame Tweaks app"})

    def test_electron_flatpak_detected(self):
        apps = {a["id"]: a for a in wp.wallet_candidates(set())}
        self.assertTrue(wp.is_electron(apps["org.notes"]))
        self.assertFalse(wp.is_electron(apps["org.kde.dolphin"]))

    def test_owner_titles_follow_the_language(self):
        # ("Set up by the “Android Mirror” tweak" stayed in the language the window opened in)
        import i18n
        english = i18n.CATALOGUE
        try:
            i18n.CATALOGUE = i18n.Catalogue(["es_419"])
            if i18n._("Android Mirror") == "Android Mirror":
                self.skipTest("no Spanish title to switch to")
            gui.sft.load(refresh=True)
            self.assertEqual(wp.wallet_owners()["android-mirror"], i18n._("Android Mirror"))
        finally:
            i18n.CATALOGUE = english
            gui.sft.load(refresh=True)
        self.assertEqual(wp.wallet_owners()["android-mirror"], "Android Mirror")

    def test_broken_launcher_link(self):
        # (a link to a menu entry that's gone: the page still opens)
        (self.own / "gone.desktop").symlink_to(self.own / "nowhere" / "gone.desktop")
        self.assertEqual([a["id"] for a in wp.protected_apps()], ["org.editor"])
        self.assertNotIn("gone", {a["id"] for a in wp.wallet_candidates({"org.editor"})})


class SystemApp(unittest.TestCase):
    def test_wrap_and_unwrap_a_system_app(self):
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        apps, sysd = t / "apps", t / "sys"
        entry(sysd, "org.kde.dolphin", "dolphin %u", DBusActivatable="true")
        out = io.StringIO()                  # (what it reports, kept out of the test output)
        with mock.patch.multiple(wl, APPS=apps, SOURCES=[], SYSTEM_SOURCES=[sysd], BACKUP_DIR=t / "orig",
                                 BUILT_DIR=t / "built"), \
                contextlib.redirect_stdout(out):
            wl.add("org.kde.dolphin", electron=False, shared=True, gate=True)
            text = (apps / "org.kde.dolphin.desktop").read_text()
            self.assertIn("X-FrameTweaks-Wallet=true", text)
            self.assertIn(f"Exec={wl.GATE} {wl.WRAPPER} dolphin %u", text)
            self.assertIn("DBusActivatable=false", text)
            wl.add("org.kde.dolphin", electron=False)           # re-wrapped (app update): gate kept
            self.assertIn(wl.GATE, (apps / "org.kde.dolphin.desktop").read_text())
            wl.add("org.kde.dolphin", electron=False, gate=False)
            self.assertNotIn(wl.GATE, (apps / "org.kde.dolphin.desktop").read_text())
            wl.remove("org.kde.dolphin")
            self.assertFalse((apps / "org.kde.dolphin.desktop").exists())     # system entry shows again
            self.assertTrue((sysd / "org.kde.dolphin.desktop").exists())
        self.assertIn("original launcher restored", out.getvalue())


at = load_script(ROOT / "packs/core/wallet" / "app-timers", "at")


class Timers(unittest.TestCase):
    def test_steps(self):
        self.assertEqual(wp.timer_step(0, 1), 5)
        self.assertEqual(wp.timer_step(15, -1), 10)
        self.assertEqual(wp.timer_step(20, 1), 30)          # a custom value snaps to a preset
        self.assertEqual(wp.timer_step(5, -1, floor=5), 5)  # Signal: can't go below 5 / off
        self.assertEqual(wp.timer_step(240, 1), 240)
        self.assertEqual(wp.timer_text(0), "Never")
        self.assertEqual(wp.timer_text(120), "2 h")

    def test_the_languages_decimal_sign(self):
        """(It was a point in every language: "1.5 u" in Dutch.)"""
        before = wp.i18n.CATALOGUE
        self.addCleanup(setattr, wp.i18n, "CATALOGUE", before)
        self.assertIn("1.5", wp.timer_text(90))
        for language, sign in (("fr", ","), ("nl_BE", ","), ("es_419", ".")):
            wp.i18n.CATALOGUE = wp.i18n.Catalogue([language])
            with self.subTest(language=language):
                self.assertIn(f"1{sign}5", wp.timer_text(90))
                self.assertIn(f"7{sign}5", wp.timer_text(7.5))

    def test_wallet_state_line(self):
        now = 1_000_000.0
        self.assertIn("locked", wp.wallet_state_text({"state": "locked"}, now))
        t = wp.wallet_state_text({"state": "unlocked", "unlocked_at": now - 31 * 60,
                                   "locks_at": now + 3 * 3600 + 5 * 60, "idle_close_minutes": 240}, now)
        self.assertIn("for 31 min", t)
        self.assertIn("in 3 h 5 min", t)
        self.assertIn("4 h unused", t)
        self.assertIn("No automatic lock", wp.wallet_state_text({"state": "unlocked"}, now))
        self.assertIn("unknown", wp.wallet_state_text(None, now))
        # SteamOS's stock wallet, without a password: the warning, locked or open
        self.assertIn("no password", wp.wallet_state_text({"state": "locked", "password": False}, now))
        self.assertNotIn("Wallet locked", wp.wallet_state_text({"state": "locked", "password": False}, now))
        t = wp.wallet_state_text({"state": "unlocked", "password": False, "unlocked_at": now - 60}, now)
        self.assertIn("no password", t)
        self.assertIn("Wallet open", t)
        self.assertNotIn("no password", wp.wallet_state_text({"state": "locked", "password": None}, now))

    def test_settings_files(self):
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        with mock.patch.multiple(at, CONF=t / "app-timers.conf", SIGNAL_CONF=t / "signal-guard.conf"):
            at.set_timer("org.notes", 30)
            at.set_timer("org.other", 10)
            at.set_timer("org.other", 0)                     # removed
            at.set_headset("org.notes", True)
            at.set_timer("org.notes", 60)                    # changing the time keeps headset
            self.assertEqual(at.read_conf(), {"org.notes": {"minutes": 60, "headset": True}})
            # Signal guard's settings carry over once, then the timer is Signal's like any app's.
            (t / "signal-guard.conf").write_text("# signal-guard settings\nIDLE_MINUTES=20\nLOCK_ON_HEADSET_OFF=1\n")
            at.import_signal_guard()
            self.assertEqual(at.read_conf()["org.signal.Signal"], {"minutes": 20, "headset": True})
            # Set to Never, it stays so when Signal is installed again (a reinstall, an update): that
            # brought its 15 minutes back.
            at.set_timer("org.signal.Signal", 0)
            (t / "signal-guard.conf").unlink()
            at.set_timer("org.x", 5)
            at.import_signal_guard()
            self.assertNotIn("org.signal.Signal", at.read_conf())
            with mock.patch("sys.argv", ["app-timers", "--list"]), contextlib.redirect_stdout(io.StringIO()) as listed:
                at.main()
            self.assertEqual(listed.getvalue(), "org.notes 60 headset\norg.x 5\n")      # (Never isn't a timer)
            (t / "app-timers.conf").unlink()
            at.import_signal_guard()                         # first time, no old settings: the 15-minute default
            self.assertEqual(at.read_conf()["org.signal.Signal"]["minutes"], 15)

    def test_an_app_id_with_spaces(self):
        # (a menu entry of your own, "My App.desktop": its timer was never read back)
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        conf = t / ".config/frame-tweaks/app-timers.conf"
        with mock.patch.multiple(at, CONF=conf, SIGNAL_CONF=t / "none"):
            at.set_timer("My App", 15)
            at.set_headset("My App", True)
            at.set_timer("org.notes", 30)
            self.assertEqual(at.read_conf(), {"My App": {"minutes": 15, "headset": True},
                                              "org.notes": {"minutes": 30, "headset": False}})
        # The page reads app-timers --list, whose app ids can have spaces too.
        env = {"HOME": str(t), "FRAME_TWEAKS_PYLIB": str(ROOT / "lib")}
        with mock.patch.object(wp, "APP_TIMERS", ROOT / "packs/core/wallet/app-timers"), mock.patch.dict(os.environ, env):
            self.assertEqual(wp.app_timers(), {"My App": (15.0, True), "org.notes": (30.0, False)})

    def test_scope_names(self):
        pat = at.scope_pattern("org.notes")
        for cg in ("/user.slice/app.slice/app-flatpak-org.notes-123.scope", "/x/app-org.notes-4.scope",
                   "/x/app-kde-org.notes@ab12.service"):
            self.assertTrue(pat.search(cg), cg)
        for cg in ("/x/app-flatpak-org.notes2-1.scope", "/x/session.slice/steam.service"):
            self.assertFalse(pat.search(cg), cg)


class LockHours(unittest.TestCase):
    """The auto-lock length the Wallet apps page sets, as wallet-unlock reads it."""
    def test_default_set_and_kept_lines(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        with mock.patch.object(wp, "LOCK_CONF", d / "wallet.conf"):
            self.assertEqual(wp.lock_hours(), 4)
            (d / "wallet.conf").write_text("OTHER=1\nWALLET_LOCK_HOURS=bad\n")
            self.assertEqual(wp.lock_hours(), 4)
            wp.set_lock_hours(8)
            self.assertEqual(wp.lock_hours(), 8)
            self.assertEqual((d / "wallet.conf").read_text(), "OTHER=1\nWALLET_LOCK_HOURS=8\n")

    def test_unticking_password_first_on_a_password_only_entry_removes_it(self):
        # (it kept the protection mark with nothing on, and read "password only")
        page = mock.Mock()
        app = {"id": "dictate", "name": "Dictate", "shared": False, "gate": True, "electron": False}
        wp.WalletApps.set_gate(page, app, False)
        page.run.assert_called_once_with(["--remove", "dictate"], "Dictate: removed")
        page.reset_mock()
        wp.WalletApps.set_gate(page, dict(app, shared=True), False)            # the shared wallet stays
        page.run.assert_called_once_with(["--no-gate", "dictate"], "Dictate: opens without asking for the password")
        page.reset_mock()
        wp.WalletApps.set_gate(page, dict(app, gate=False), True)
        page.run.assert_called_once_with(["--gate", "--no-shared", "dictate"], "Dictate: asks for the wallet password first")

    def test_dry_run_saves_nothing(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        with mock.patch.object(wp, "LOCK_CONF", d / "wallet.conf"), contextlib.redirect_stdout(io.StringIO()) as out, \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}):
            wp.WalletApps.step_hours(mock.Mock(), +1)         # the + beside the auto-lock time
        self.assertFalse((d / "wallet.conf").exists())
        self.assertIn("would save: WALLET_LOCK_HOURS=6", out.getvalue())


class NoPassword(unittest.TestCase):
    """--info saying the wallet has no password (SteamOS's stock wallet): the page warns, Unlock
    becomes Open (no dialog to wait for) and a Set password button starts KWalletManager."""
    def test_the_page_says_so_and_offers_kwalletmanager(self):
        from PyQt6.QtWidgets import QApplication, QWidget
        app = QApplication.instance() or QApplication([])   # noqa: F841  (kept alive for the page)
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        unlock = t / "wallet-unlock"
        unlock.write_text('#!/bin/bash\n[ "$1" = --info ] && { echo \'{"state": "locked", "password": false}\'; exit; }\n')
        unlock.chmod(0o755)
        (t / "apps").mkdir()
        (t / "apps/org.kde.kwalletmanager.desktop").write_text("[Desktop Entry]\nName=KWalletManager\nExec=true\n")

        class Window(QWidget):
            def go_back(self):
                pass
        with mock.patch.multiple(wp, WALLET_UNLOCK=unlock, APP_TIMERS=t / "none", LAUNCHERS=t / "apps",
                                 FLATPAK_APPS=[], SYSTEM_APPS=[], FLATPAK_ROOTS=[], LOCK_CONF=t / "wallet.conf"), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}):
            page = wp.WalletApps(Window())
            self.assertIn("no password", page.wallet_state.text())
            self.assertFalse(page.set_password.isHidden())
            self.assertIn("Open", page.wallet_toggle.text())
            self.assertNotIn("…", page.wallet_toggle.text())
            with contextlib.redirect_stdout(io.StringIO()) as out:
                page.open_kwalletmanager()
                page.toggle_wallet()
            self.assertIn("would run: gtk-launch org.kde.kwalletmanager", out.getvalue())
            self.assertIn("would run: wallet-unlock", out.getvalue())
            self.assertNotIn("Waiting for the wallet password", page.wallet_state.text())
            # with a password, or unknown: no button
            unlock.write_text('#!/bin/bash\n[ "$1" = --info ] && { echo \'{"state": "locked", "password": true}\'; exit; }\n')
            page.show_wallet_state()
            self.assertTrue(page.set_password.isHidden())
            self.assertIn("Unlock", page.wallet_toggle.text())
            (t / "apps/org.kde.kwalletmanager.desktop").unlink()      # (no KWalletManager: no button to start it)
            unlock.write_text('#!/bin/bash\n[ "$1" = --info ] && { echo \'{"state": "locked", "password": false}\'; exit; }\n')
            page.show_wallet_state()
            self.assertTrue(page.set_password.isHidden())
            self.assertIn("no password", page.wallet_state.text())


class Tooltips(unittest.TestCase):
    def test_every_button_without_a_word_has_one(self):
        """The auto-lock time's − and + had none: in VR, nothing said what they changed."""
        from PyQt6.QtWidgets import QApplication, QWidget
        app = QApplication.instance() or QApplication([])   # noqa: F841  (kept alive for the page)
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        unlock = t / "wallet-unlock"
        unlock.write_text('#!/bin/bash\n[ "$1" = --info ] && { echo \'{"state": "locked", "password": true}\'; exit; }\n')
        unlock.chmod(0o755)
        entry(t / "apps", "org.notes", "/home/u/.local/bin/frame-outer-bus flatpak run org.notes",
              **{"X-FrameTweaks-Wallet": "true"})

        class Window(QWidget):
            def go_back(self):
                pass
        with mock.patch.multiple(wp, WALLET_UNLOCK=unlock, APP_TIMERS=t / "none", LAUNCHERS=t / "apps",
                                 FLATPAK_APPS=[], SYSTEM_APPS=[], FLATPAK_ROOTS=[], LOCK_CONF=t / "wallet.conf"), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}):
            page = wp.WalletApps(Window())
            self.assertEqual((page.shorter.text(), page.longer.text()), ("−", "+"))
            self.assertEqual(untipped_icon_buttons(page, hidden=True), [])


class Background(unittest.TestCase):
    """🔓 Unlock… (wallet-unlock, waiting for its password) keeps running when the page is
    closed, and its end leaves the closed page alone (that showed the error page)."""
    def test_unlock_outlives_the_page(self):
        from PyQt6.QtCore import QCoreApplication, QEvent, QProcess
        from PyQt6.QtWidgets import QApplication, QWidget
        app = QApplication.instance() or QApplication([])
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        unlock = t / "wallet-unlock"           # (a stand-in: locked, and unlocks after a moment)
        unlock.write_text('#!/bin/bash\n[ "$1" = --info ] && { echo \'{"state": "locked"}\'; exit; }\n'
                          f"sleep 0.5; touch {t}/unlocked\n")
        unlock.chmod(0o755)

        class Window(QWidget):
            def go_back(self):
                pass
        errors = []
        with mock.patch.multiple(wp, WALLET_UNLOCK=unlock, APP_TIMERS=t / "none", LAUNCHERS=t / "apps",
                                 FLATPAK_APPS=[], SYSTEM_APPS=[], FLATPAK_ROOTS=[], LOCK_CONF=t / "wallet.conf"), \
                mock.patch.object(sys, "excepthook", lambda *a: errors.append(a[1])), mock.patch.dict(os.environ):
            os.environ.pop("FRAME_TWEAKS_DRY_RUN", None)
            window = Window()
            page = wp.WalletApps(window)
            page.setParent(window)
            page.toggle_wallet()                   # 🔓 Unlock…
            page.deleteLater()                     # ← Back
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            running = lambda: [p for p in window.findChildren(QProcess) if p.state() != QProcess.ProcessState.NotRunning]
            for _ in range(200):
                app.processEvents()                # (its finished signal, once it's done)
                if (t / "unlocked").exists() and not running():
                    break
                time.sleep(0.05)
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertTrue((t / "unlocked").exists())
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()


class AllHomebrewCommands(unittest.TestCase):
    """Show all Homebrew commands: off when the page opens (wallet-tool isn't asked for them);
    on, a row a formula with a check box a command, and Protect selected protects just those."""
    def test_off_by_default_then_pick_and_protect(self):
        from PyQt6.QtWidgets import QApplication, QCheckBox, QPushButton, QWidget
        app = QApplication.instance() or QApplication([])   # noqa: F841  (kept alive for the page)
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        unlock = t / "wallet-unlock"
        unlock.write_text('#!/bin/bash\n[ "$1" = --info ] && { echo \'{"state": "locked", "password": true}\'; exit; }\n')
        tool = t / "wallet-tool"
        tool.write_text(f'#!/bin/bash\necho "$*" >> {t}/asked\ncase "$*" in\n'
                        '  --list) printf "gh\\t/hb/gh\\n" ;;\n  --candidates) printf "rg\\tripgrep\\n" ;;\n'
                        '  "--candidates --all") printf "rg\\tripgrep\\t\\npcre2grep\\tpcre2\\tdependency\\n'
                        'pcre2test\\tpcre2\\tdependency\\nwhisper-cli\\twhisper.cpp\\ttweak\\n" ;;\nesac\n')
        for f in (unlock, tool):
            f.chmod(0o755)

        class Window(QWidget):
            def go_back(self):
                pass
        with mock.patch.multiple(wp, WALLET_UNLOCK=unlock, WALLET_TOOL=tool, APP_TIMERS=t / "none", LAUNCHERS=t / "none",
                                 FLATPAK_APPS=[], SYSTEM_APPS=[], FLATPAK_ROOTS=[], LOCK_CONF=t / "wallet.conf"), \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}):
            page = wp.WalletApps(Window())
            settle(page)
            self.assertNotIn("--all", (t / "asked").read_text())
            toggle = next(b for b in page.findChildren(QPushButton) if b.text().startswith("Show all Homebrew"))
            self.assertFalse(toggle.isChecked())
            self.assertFalse([c for c in page.findChildren(QCheckBox) if c.text() == "pcre2grep"])
            toggle.setChecked(True)
            for _i in range(3):
                app.processEvents()
            settle(page)
            boxes = {c.text(): c for c in page.findChildren(QCheckBox) if not sip.isdeleted(c)}
            self.assertLessEqual({"pcre2grep", "pcre2test", "whisper-cli"}, set(boxes))
            self.assertNotIn("rg", boxes)                                  # (already offered above)
            boxes["pcre2test"].setChecked(True)
            protect = [b for b in page.findChildren(QPushButton) if not sip.isdeleted(b) and b.text() == "Protect selected"
                       and b.isEnabled()]
            self.assertEqual(len(protect), 1)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                protect[0].click()
            self.assertEqual(out.getvalue(), "would run: wallet-tool pcre2test\n")


def settle(page):
    """Until what the page asks Homebrew in the background (wallet-tool) is in."""
    from PyQt6.QtWidgets import QApplication
    for _i in range(500):
        QApplication.processEvents()
        if page.tools_job is None and page.all_tools_job is None:
            QApplication.processEvents()                       # (its fill, queued)
            return
        time.sleep(0.01)
    raise AssertionError("still asking")


class NothingHoldsUpTheWindow(unittest.TestCase):
    """Homebrew (wallet-tool, up to 90 s) was asked on the window's thread as the page opened, and
    app-timers, wallet-launcher and wallet-tool's own commands ran there with no time limit: one
    that hung, hung the window for good."""
    def setUp(self):
        from PyQt6.QtWidgets import QApplication, QWidget
        self.app = QApplication.instance() or QApplication([])
        self.t = t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        unlock = t / "wallet-unlock"
        unlock.write_text('#!/bin/bash\n[ "$1" = --info ] && { echo \'{"state": "locked", "password": true}\'; exit; }\n')
        self.tool = t / "wallet-tool"
        self.tool.write_text('#!/bin/bash\nsleep 1.5\ncase "$*" in\n  --list) printf "gh\\t/hb/gh\\n" ;;\n'
                             '  --candidates) printf "rg\\tripgrep\\n" ;;\nesac\n')
        self.timers = t / "app-timers"
        self.timers.write_text('#!/bin/bash\n[ "$1" = --list ] && exit 0\nexec sleep 30\n')
        for f in (unlock, self.tool, self.timers):
            f.chmod(0o755)

        class Window(QWidget):
            def go_back(self):
                pass
        self.Window = Window
        for p in (mock.patch.multiple(wp, WALLET_UNLOCK=unlock, WALLET_TOOL=self.tool, APP_TIMERS=self.timers,
                                      WALLET_LAUNCHER=self.timers, LAUNCHERS=t / "none", FLATPAK_APPS=[],
                                      SYSTEM_APPS=[], FLATPAK_ROOTS=[], LOCK_CONF=t / "wallet.conf", QUICK=1),
                  mock.patch.dict(os.environ)):
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("FRAME_TWEAKS_DRY_RUN", None)

    def test_homebrew_is_asked_in_the_background(self):
        start = time.monotonic()
        page = wp.WalletApps(self.Window())
        self.assertLess(time.monotonic() - start, 1)
        settle(page)
        self.assertEqual(page.tools, ([("gh", "/hb/gh")], [("rg", "ripgrep")]))

    def test_a_command_that_doesnt_answer_is_said(self):
        page = wp.WalletApps(self.Window())
        app = {"id": "org.notes", "name": "Notes"}
        for act in (lambda: page.set_timer(app, 15), lambda: page.set_headset(app, True),
                    lambda: page.run(["org.notes"], "protected")):
            start = time.monotonic()
            act()
            self.assertLess(time.monotonic() - start, 5)
            self.assertIn("didn't answer within 1 s", page.notice.text())
            page.notice.setText("")
        settle(page)
