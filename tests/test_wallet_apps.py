"""Wallet apps: the installer window's app lists, and wallet-launcher wrapping a system app."""
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gui", ROOT / "gui" / "frame-tweaks-gui.py")
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)
loader = importlib.machinery.SourceFileLoader("wl", str(ROOT / "wallet" / "wallet-launcher"))
wl = importlib.util.module_from_spec(importlib.util.spec_from_loader("wl", loader))
loader.exec_module(wl)


def entry(d, app_id, exec_line, **extra):
    d.mkdir(parents=True, exist_ok=True)
    lines = ["[Desktop Entry]", "Type=Application", f"Name={app_id.title()}", f"Exec={exec_line}"]
    lines += [f"{k}={v}" for k, v in extra.items()]
    (d / f"{app_id}.desktop").write_text("\n".join(lines) + "\n")


class Lists(unittest.TestCase):
    def setUp(self):
        t = Path(tempfile.mkdtemp())
        self.own, self.flat, self.sys, self.roots = t / "own", t / "flat", t / "sys", t / "roots"
        entry(self.flat, "org.notes", "flatpak run org.notes")
        (self.roots / "org.notes/current/active/files/notes").mkdir(parents=True)
        (self.roots / "org.notes/current/active/files/notes/resources.pak").touch()
        entry(self.flat, "org.editor", "flatpak run org.editor")
        entry(self.sys, "org.kde.dolphin", "dolphin %u")
        entry(self.sys, "hidden-helper", "helper", NoDisplay="true")
        entry(self.own, "Some Game", "steam steam://rungameid/123")
        entry(self.own, "mytool", "/opt/mytool/run")
        entry(self.own, "org.editor", "/home/u/.local/bin/frame-outer-bus flatpak run org.editor", **{"X-FrameTweaks-Wallet": "true"})
        self.patch = mock.patch.multiple(gui, LAUNCHERS=self.own, FLATPAK_APPS=[self.flat],
                                         SYSTEM_APPS=[self.sys], FLATPAK_ROOTS=[self.roots])
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_every_kind_of_installed_app_is_offered_once(self):
        protected = gui.protected_apps()
        self.assertEqual([a["id"] for a in protected], ["org.editor"])
        self.assertTrue(protected[0]["shared"])
        offered = {a["id"]: a["kind"] for a in gui.wallet_candidates({"org.editor"})}
        # Steam shortcuts, hidden entries and protected apps aren't offered.
        self.assertEqual(offered, {"org.notes": "Flatpak", "org.kde.dolphin": "System app", "mytool": "Your app"})

    def test_electron_flatpak_detected(self):
        apps = {a["id"]: a for a in gui.wallet_candidates(set())}
        self.assertTrue(gui.is_electron(apps["org.notes"]))
        self.assertFalse(gui.is_electron(apps["org.kde.dolphin"]))


class SystemApp(unittest.TestCase):
    def test_wrap_and_unwrap_a_system_app(self):
        t = Path(tempfile.mkdtemp())
        apps, sysd = t / "apps", t / "sys"
        entry(sysd, "org.kde.dolphin", "dolphin %u", DBusActivatable="true")
        with mock.patch.multiple(wl, APPS=apps, SOURCES=[], SYSTEM_SOURCES=[sysd], BACKUP_DIR=t / "orig"):
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


loader2 = importlib.machinery.SourceFileLoader("at", str(ROOT / "wallet" / "app-timers"))
at = importlib.util.module_from_spec(importlib.util.spec_from_loader("at", loader2))
loader2.exec_module(at)


class Timers(unittest.TestCase):
    def test_steps(self):
        self.assertEqual(gui.timer_step(0, 1), 5)
        self.assertEqual(gui.timer_step(15, -1), 10)
        self.assertEqual(gui.timer_step(20, 1), 30)          # a custom value snaps to a preset
        self.assertEqual(gui.timer_step(5, -1, floor=5), 5)  # Signal: can't go below 5 / off
        self.assertEqual(gui.timer_step(240, 1), 240)
        self.assertEqual(gui.timer_text(0), "Never")
        self.assertEqual(gui.timer_text(120), "2 h")

    def test_settings_files(self):
        t = Path(tempfile.mkdtemp())
        guard = t / "signal-guard"
        with mock.patch.multiple(at, CONF=t / "app-timers.conf", SIGNAL_CONF=t / "signal-guard.conf",
                                 SIGNAL_GUARD=guard):
            at.set_timer("org.notes", 30)
            at.set_timer("org.other", 10)
            at.set_timer("org.other", 0)                     # removed
            self.assertEqual(at.all_timers(), {"org.notes": 30})
            guard.touch()                                    # Signal guard installed: its own file
            (t / "signal-guard.conf").write_text("# signal-guard settings\nIDLE_MINUTES=15\nLOCK_ON_HEADSET_OFF=0\n")
            at.set_timer("org.signal.Signal", 60)
            self.assertIn("IDLE_MINUTES=60\nLOCK_ON_HEADSET_OFF=0", (t / "signal-guard.conf").read_text())
            self.assertEqual(at.all_timers(), {"org.notes": 30, "org.signal.Signal": 60})
            self.assertNotIn("Signal", (t / "app-timers.conf").read_text())

    def test_scope_names(self):
        pat = at.scope_pattern("org.notes")
        for cg in ("/user.slice/app.slice/app-flatpak-org.notes-123.scope", "/x/app-org.notes-4.scope",
                   "/x/app-kde-org.notes@ab12.service"):
            self.assertTrue(pat.search(cg), cg)
        for cg in ("/x/app-flatpak-org.notes2-1.scope", "/x/session.slice/steam.service"):
            self.assertFalse(pat.search(cg), cg)


if __name__ == "__main__":
    unittest.main()
