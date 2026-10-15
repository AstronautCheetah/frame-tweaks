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
from helpers import load_script  # noqa: E402
gui = load_script(ROOT / "gui" / "frame-tweaks-gui.py", "gui")
import wallet_page as wp  # noqa: E402  (the window's Wallet apps page; gui put it on sys.path)
wl = load_script(ROOT / "packs/original/wallet" / "wallet-launcher", "wl")


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
        with mock.patch.multiple(wl, APPS=apps, SOURCES=[], SYSTEM_SOURCES=[sysd], BACKUP_DIR=t / "orig"), \
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


at = load_script(ROOT / "packs/original/wallet" / "app-timers", "at")


class Timers(unittest.TestCase):
    def test_steps(self):
        self.assertEqual(wp.timer_step(0, 1), 5)
        self.assertEqual(wp.timer_step(15, -1), 10)
        self.assertEqual(wp.timer_step(20, 1), 30)          # a custom value snaps to a preset
        self.assertEqual(wp.timer_step(5, -1, floor=5), 5)  # Signal: can't go below 5 / off
        self.assertEqual(wp.timer_step(240, 1), 240)
        self.assertEqual(wp.timer_text(0), "Never")
        self.assertEqual(wp.timer_text(120), "2 h")

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
            at.set_timer("org.signal.Signal", 0)
            (t / "signal-guard.conf").unlink()
            at.set_timer("org.x", 5)
            at.import_signal_guard()                         # no old settings: the 15-minute default
            self.assertEqual(at.read_conf()["org.signal.Signal"]["minutes"], 15)

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

    def test_dry_run_saves_nothing(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        with mock.patch.object(wp, "LOCK_CONF", d / "wallet.conf"), contextlib.redirect_stdout(io.StringIO()) as out, \
                mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"}):
            wp.WalletApps.step_hours(mock.Mock(), +1)         # the + beside the auto-lock time
        self.assertFalse((d / "wallet.conf").exists())
        self.assertIn("would save: WALLET_LOCK_HOURS=6", out.getvalue())


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
