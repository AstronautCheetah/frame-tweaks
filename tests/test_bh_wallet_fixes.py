"""The wallet tweak's menu-entry wrapping (wallet-launcher), app timers finding an app's
processes, and its uninstall and status scripts, each in a throwaway home folder."""
import sys
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
WALLET = ROOT / "packs/core/wallet"


def load(name, home):
    """A fresh copy of one of the wallet's programs, with its paths in this home folder."""
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(WALLET / name))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    with mock.patch.dict(os.environ, {"HOME": str(home)}):
        loader.exec_module(module)
    return module


def entry(path, exec_line, *extra):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(["[Desktop Entry]", "Type=Application", "Name=App", f"Exec={exec_line}", *extra]) + "\n")


class Home(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.flat, self.sysd = self.home / "flatpak-exports", self.home / "system-apps"
        patch = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patch.start()
        self.addCleanup(patch.stop)


class Launcher(Home):
    def setUp(self):
        super().setUp()
        self.wl = load("wallet-launcher", self.home)
        self.wl.SOURCES, self.wl.SYSTEM_SOURCES = [self.flat], [self.sysd]
        self.apps, self.orig = self.wl.APPS, self.wl.BACKUP_DIR

    def launcher(self, *args):
        with mock.patch("sys.argv", ["wallet-launcher", *args]), mock.patch("os.system"), \
                contextlib.redirect_stdout(io.StringIO()):
            self.wl.main()

    def test_your_override_of_a_flatpak_entry_is_kept_and_given_back(self):
        entry(self.flat / "org.notes.desktop", "/usr/bin/flatpak run --branch=stable org.notes @@u %U @@")
        entry(self.apps / "org.notes.desktop", "/usr/bin/flatpak run --branch=stable org.notes --mine @@u %U @@",
              "Name[de]=Meine Notizen")
        mine = (self.apps / "org.notes.desktop").read_text()
        self.launcher("--gate", "org.notes")
        wrapped = (self.apps / "org.notes.desktop").read_text()
        self.assertIn("--mine", wrapped)                        # wrapped from yours, not the export's
        self.assertIn(self.wl.GATE, wrapped)
        self.assertEqual((self.orig / "org.notes.desktop").read_text(), mine)
        self.launcher("--remove", "org.notes")
        self.assertEqual((self.apps / "org.notes.desktop").read_text(), mine)

    def test_a_new_entry_written_over_the_wrapper_becomes_the_original(self):
        entry(self.apps / "my.app.desktop", "/opt/app/v1 %U")
        self.launcher("--gate", "my.app")
        entry(self.apps / "my.app.desktop", "/opt/app/v2 %U")        # the app's installer, after an update
        self.launcher("--gate", "my.app")
        self.assertIn("/opt/app/v2", (self.apps / "my.app.desktop").read_text())
        self.assertIn("/opt/app/v2", (self.orig / "my.app.desktop").read_text())

    def test_password_first_alone_still_runs_exec(self):
        entry(self.flat / "org.kde.wm.desktop", "/usr/bin/flatpak run org.kde.wm @@ %F @@", "DBusActivatable=true")
        self.launcher("--gate", "--no-shared", "org.kde.wm")
        text = (self.apps / "org.kde.wm.desktop").read_text()
        self.assertIn("DBusActivatable=false", text)         # D-Bus activation would skip the gate
        self.assertIn(f"Exec={self.wl.GATE} /usr/bin/flatpak run org.kde.wm", text)
        self.launcher("--no-gate", "--no-shared", "org.kde.wm")
        self.assertIn("DBusActivatable=true", (self.apps / "org.kde.wm.desktop").read_text())

    def test_password_store_goes_to_the_program(self):
        rw = self.wl.rewrite_exec
        self.assertEqual(rw("env ELECTRON_OZONE_PLATFORM_HINT=wayland /opt/chat/chat %U", "chat", True, shared=False),
                         "env ELECTRON_OZONE_PLATFORM_HINT=wayland /opt/chat/chat --password-store=kwallet6 %U")
        self.assertEqual(rw("/usr/bin/flatpak run --branch=stable org.chat @@u %U @@", "org.chat", True, shared=False),
                         "/usr/bin/flatpak run --branch=stable org.chat --password-store=kwallet6 @@u %U @@")
        self.assertEqual(rw("/opt/chat/chat %U", "chat", True, shared=False), "/opt/chat/chat --password-store=kwallet6 %U")

    def test_reapply_without_a_wrapper_puts_the_new_original_in_the_menu(self):
        # A protected Frame Tweaks entry; its tweak uninstalled (entry removed, original kept), then
        # installed again: install_desktop writes the new version as the original and reapplies.
        entry(self.apps / "dictate.desktop", "/home/u/.local/bin/dictate")
        self.launcher("--gate", "dictate")
        (self.apps / "dictate.desktop").unlink()
        entry(self.orig / "dictate.desktop", "/home/u/.local/bin/dictate --new")
        self.launcher("--reapply", "dictate")
        self.assertIn("dictate --new", (self.apps / "dictate.desktop").read_text())
        self.assertFalse((self.orig / "dictate.desktop").exists())


class Timers(Home):
    def setUp(self):
        super().setUp()
        self.at = load("app-timers", self.home)

    def program(self, exec_line):
        entry(self.home / ".local/share/applications/test.bh.app.desktop", exec_line)
        return self.at.host_program("test.bh.app")

    def test_shells_and_interpreters_are_not_the_app(self):
        # Their processes include the session's scripts: a timer must never quit those.
        for line in ("sh -c 'xdg-open appstream://org.chromium.Chromium' %U", "bash -c 'exec x'",
                     "env A=1 python3 /opt/notes/main.py", f"{self.home}/.local/bin/wallet-gate sh -c x"):
            self.assertIsNone(self.program(line), line)
            self.assertEqual(self.at.host_main_pids("test.bh.app"), [], line)

    def test_a_program_of_its_own_is_found(self):
        prog = self.home / "opt/app/run"
        prog.parent.mkdir(parents=True)
        prog.write_text("")
        prog.chmod(0o755)
        self.assertEqual(self.program(f"{self.home}/.local/bin/frame-outer-bus {prog} %U"), os.path.realpath(prog))


class OneDialog(Home):
    """Two unlock requests at once (Firefox started twice, a git push beside a gh call): one
    password dialog; the other waits for it and takes its answer, unlocked or cancelled."""
    def wallet_unlock(self):
        """wallet-unlock with stand-ins for its D-Bus library (jeepney: not in every Python
        here), and the shared modules from this checkout."""
        import types
        fake = {n: types.ModuleType(n) for n in ("jeepney", "jeepney.bus_messages", "jeepney.io", "jeepney.io.blocking")}
        fake["jeepney"].DBusAddress = lambda *a, **k: None
        fake["jeepney"].MessageType = types.SimpleNamespace(error=3, signal=4)
        fake["jeepney"].new_method_call = lambda *a, **k: None
        fake["jeepney.bus_messages"].message_bus = None
        fake["jeepney.io.blocking"].open_dbus_connection = lambda *a, **k: None
        with mock.patch.dict(sys.modules, fake), mock.patch.dict(os.environ, {"FRAME_TWEAKS_PYLIB": str(ROOT / "lib")}):
            return load("wallet-unlock", self.home)

    def run_two(self, answer):
        import threading
        wu = self.wallet_unlock()
        wu.ASKING, wu.CANCELLED = self.home / "asking.lock", self.home / "cancelled"
        state = {"locked": True, "dialogs": 0}
        first_open, may_answer = threading.Event(), threading.Event()

        def unlock(conn):                     # the dialog: open until told to answer
            state["dialogs"] += 1
            first_open.set()
            may_answer.wait(10)
            state["locked"] = not answer
            return answer
        results = {}
        with mock.patch.object(wu, "unlock", unlock), mock.patch.object(wu, "is_locked", lambda conn: state["locked"]), \
                contextlib.redirect_stderr(io.StringIO()):
            a = threading.Thread(target=lambda: results.__setitem__("a", wu.ask_once(None)))
            a.start()
            self.assertTrue(first_open.wait(10))
            b = threading.Thread(target=lambda: results.__setitem__("b", wu.ask_once(None)))
            b.start()
            b.join(0.5)
            self.assertTrue(b.is_alive())              # (waiting for the open dialog)
            may_answer.set()
            a.join(10)
            b.join(10)
        return results, state["dialogs"]

    def test_the_second_request_takes_the_first_dialogs_unlock(self):
        self.assertEqual(self.run_two(True), ({"a": "unlocked", "b": "already"}, 1))

    def test_a_cancelled_dialog_isnt_followed_by_another(self):
        self.assertEqual(self.run_two(False), ({"a": None, "b": None}, 1))


class Scripts(Home):
    """uninstall.sh and status.sh with stand-ins for systemctl and the wallet's programs."""
    def setUp(self):
        super().setUp()
        self.bin, self.stubs = self.home / ".local/bin", self.home / "stubs"
        for d in (self.bin, self.stubs):
            d.mkdir(parents=True)

    def tool(self, folder, name, body):
        stub(folder, name, body)

    def run_script(self, name):
        env = sandbox_env(self.home, self.stubs, USER="test")
        return subprocess.run(["bash", str(WALLET / name)], env=env, capture_output=True, text=True, timeout=60)

    def test_uninstall_restores_an_entry_whose_name_has_spaces(self):
        self.tool(self.stubs, "systemctl", "exit 0")
        (self.bin / "wallet-launcher").write_bytes((WALLET / "wallet-launcher").read_bytes())
        (self.bin / "wallet-launcher").chmod(0o755)
        apps, orig = self.home / ".local/share/applications", self.home / ".local/share/frame-tweaks/launcher-originals"
        entry(orig / "My App.desktop", "/opt/my-app/run %U")
        original = (orig / "My App.desktop").read_text()
        entry(apps / "My App.desktop", f"{self.bin}/wallet-gate /opt/my-app/run %U", "X-FrameTweaks-Wallet=true")
        entry(apps / "Other.desktop", "/opt/other")
        r = self.run_script("uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((apps / "My App.desktop").read_text(), original)    # not left pointing at wallet-gate
        self.assertTrue((apps / "Other.desktop").exists())

    def status(self, autolock=None):
        # Services running, the wallet unlocked, no auto-lock timer.
        self.tool(self.stubs, "systemctl", '[ "$4" = wallet-autolock.timer ] && exit 3; exit 0')
        self.tool(self.bin, "wallet-unlock", "echo unlocked")
        self.tool(self.bin, "wallet-launcher", "exit 0")
        if autolock is not None:
            (self.home / ".config/frame-tweaks").mkdir(parents=True, exist_ok=True)
            (self.home / ".config/frame-tweaks/wallet.conf").write_text(f"WALLET_LOCK_HOURS=4\nWALLET_AUTOLOCK={autolock}\n")
        return self.run_script("status.sh")

    def test_status_warns_about_an_unlocked_wallet_without_its_auto_lock(self):
        r = self.status()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("no auto-lock scheduled", r.stdout)
        self.assertEqual(self.status(autolock=1).returncode, 2)

    def test_status_is_ok_when_auto_lock_was_turned_off(self):
        r = self.status(autolock=0)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("wallet unlocked", r.stdout)


if __name__ == "__main__":
    unittest.main()
