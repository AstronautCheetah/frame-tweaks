"""The wallet tweak's menu-entry wrapping (wallet-launcher), app timers finding an app's
processes and deciding when to close one, wallet-unlock's auto-lock, watcher and prompt broker,
and its install, uninstall and status scripts, each in a throwaway home folder."""
import sys
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import select as select_module
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import types
import unittest
from collections import deque
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import kde_saves, sandbox_env, stub  # noqa: E402
WALLET = ROOT / "packs/core/wallet"


def load(name, home):
    """A fresh copy of one of the wallet's programs, with its paths in this home folder."""
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(WALLET / name))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    with mock.patch.dict(os.environ, {"HOME": str(home)}):
        loader.exec_module(module)
    return module


def jeepney_stand_ins():
    """Stand-ins for wallet-unlock's D-Bus library (jeepney: not in every Python here). A message
    is a tuple saying what it asks: ("call", method), ("NameHasOwner", name), ("AddMatch", rule).
    Nothing reaches a real bus."""
    fake = {n: types.ModuleType(n) for n in ("jeepney", "jeepney.bus_messages", "jeepney.io", "jeepney.io.blocking")}
    fake["jeepney"].DBusAddress = lambda *a, **k: k.get("bus_name")
    fake["jeepney"].MessageType = types.SimpleNamespace(method_return=2, error=3, signal=4)
    # (kwalletd6's calls say so: ("call", "kwalletd6.isOpen"); ksecretd's and the rest's don't)
    fake["jeepney"].new_method_call = lambda address, method, *a: (
        "call", f"kwalletd6.{method}" if address == "org.kde.kwalletd6" else method)

    class MatchRule(dict):
        def add_arg_condition(self, argno, value):
            self[f"arg{argno}"] = value
    fake["jeepney"].MatchRule = MatchRule
    fake["jeepney.bus_messages"].message_bus = types.SimpleNamespace(
        NameHasOwner=lambda name: ("NameHasOwner", name), AddMatch=lambda rule: ("AddMatch", rule),
        StartServiceByName=lambda name: ("StartServiceByName", name),
        GetNameOwner=lambda name: ("GetNameOwner", name),
        GetConnectionUnixProcessID=lambda name: ("GetConnectionUnixProcessID", name))

    def no_bus(*a, **k):
        raise AssertionError("a test reached for a real D-Bus")
    fake["jeepney.io.blocking"].open_dbus_connection = no_bus
    return fake


def wallet_unlock(home):
    """wallet-unlock with stand-ins for jeepney, the shared modules from this checkout, and its
    files in /run/user (the session, the dialog's and the auto-lock's locks) in home instead."""
    with mock.patch.dict(sys.modules, jeepney_stand_ins()), \
            mock.patch.dict(os.environ, {"FRAME_TWEAKS_PYLIB": str(ROOT / "lib")}):
        wu = load("wallet-unlock", home)
    wu.SESSION, wu.ASKING, wu.CANCELLED, wu.SCHEDULING = (
        home / name for name in ("wallet-session.json", "asking.lock", "cancelled", "autolock.lock"))
    return wu


class Done(Exception):
    """Ends one of the programs' endless loops in a test."""


class FakeConn:
    """A session bus connection as jeepney's blocking one behaves: send_and_get_reply waits for
    its reply, and drops whatever else arrives meanwhile (there's no filter). answer(message)
    gives a reply's body; incoming: the signals still to come, once the match rules are in."""
    def __init__(self, answer, incoming=()):
        self.answer, self.incoming, self.sent = answer, deque(incoming), []

    def send_and_get_reply(self, message):
        self.sent.append(message)
        if message[0] != "AddMatch":
            self.incoming.clear()           # (arrived while it waited for its reply: dropped)
        return types.SimpleNamespace(header=types.SimpleNamespace(message_type=2, fields={}), body=self.answer(message))

    def send(self, message):
        self.answer(message)

    def receive(self, timeout=None):
        if not self.incoming:
            raise Done
        return self.incoming.popleft()

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def wallet_signal(member, body=("kdewallet",)):
    return types.SimpleNamespace(header=types.SimpleNamespace(message_type=4, fields={3: member}), body=body)


def ksecretd(state):
    """Replies as ksecretd: running if state["running"] (default), the wallet open unless
    state["locked"]; a close or Lock locks it."""
    def answer(message):
        kind, what = message
        if kind == "NameHasOwner":
            return (state.get("running", True),)
        if what == "isOpen":
            return (not state["locked"],)
        if what in ("close", "Lock"):
            state["locked"] = True
        return ()
    return answer


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

    def test_list_passes_over_a_broken_link(self):
        # (it stopped there, and the wallet's status said "not installed")
        entry(self.apps / "org.notes.desktop", "/opt/notes", "X-FrameTweaks-Wallet=true")
        (self.apps / "gone.desktop").symlink_to(self.home / "nowhere" / "gone.desktop")
        with mock.patch("sys.argv", ["wallet-launcher", "--list"]), mock.patch("os.system"), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.wl.main()
        self.assertEqual(out.getvalue().split(), ["org.notes"])

    def test_your_name_and_icon_stay_when_it_is_wrapped_again(self):
        """A rename in KDE's menu editor (saved into the wrapper itself) went back the next time
        the app was wrapped again: the wallet's install does it at every update."""
        entry(self.flat / "org.notes.desktop", "/usr/bin/flatpak run --branch=stable org.notes @@u %U @@",
              "Icon=org.notes", "Comment=Notes")
        self.launcher("--gate", "org.notes")
        menu = self.apps / "org.notes.desktop"
        menu.write_text(kde_saves(menu.read_text(), Name="My notes", Icon="my-notes"))
        entry(self.flat / "org.notes.desktop", "/usr/bin/flatpak run --branch=stable org.notes --new @@u %U @@",
              "Icon=org.notes", "Comment=Notes, everywhere")           # (the app updated meanwhile)
        self.launcher("--gate", "org.notes")
        lines = menu.read_text().splitlines()
        for line in ("Name=My notes", "Icon=my-notes", "Comment=Notes, everywhere", "X-FrameTweaks-Wallet=true",
                     f"Exec={self.wl.GATE} {self.wl.WRAPPER} /usr/bin/flatpak run --branch=stable "
                     "--talk-name=org.kde.kwalletd6 --talk-name=org.freedesktop.secrets org.notes --new @@u %U @@"):
            self.assertIn(line, lines)
        self.assertEqual(lines[0], "[Desktop Entry]")                  # (KDE had sorted the groups)

    def test_your_command_options_stay_wrapped_as_asked(self):
        entry(self.flat / "org.notes.desktop", "/usr/bin/flatpak run --branch=stable org.notes @@u %U @@")
        self.launcher("--gate", "org.notes")
        menu = self.apps / "org.notes.desktop"

        def command():
            return next(line[5:] for line in menu.read_text().splitlines() if line.startswith("Exec="))
        menu.write_text(kde_saves(menu.read_text(), Exec=command().replace(" @@u", " --dark @@u")))
        talk = "--talk-name=org.kde.kwalletd6 --talk-name=org.freedesktop.secrets"
        self.launcher("--gate", "org.notes")
        self.assertEqual(command(), f"{self.wl.GATE} {self.wl.WRAPPER} /usr/bin/flatpak run --branch=stable {talk} "
                                    "org.notes --dark @@u %U @@")
        self.launcher("--no-gate", "--no-shared", "org.notes")        # (what it added goes with its option)
        self.assertEqual(command(), "/usr/bin/flatpak run --branch=stable org.notes --dark @@u %U @@")
        self.launcher("--gate", "--electron", "org.notes")
        self.launcher("--gate", "org.notes")                          # (once, however often it's rebuilt)
        self.assertEqual(command(), f"{self.wl.GATE} {self.wl.WRAPPER} /usr/bin/flatpak run --branch=stable {talk} "
                                    "org.notes --password-store=kwallet6 --dark @@u %U @@")
        self.launcher("--remove", "org.notes")
        self.assertEqual(command(), "/usr/bin/flatpak run --branch=stable org.notes --dark @@u %U @@")

    def test_a_wrapper_from_before_gets_its_copy_if_it_is_unchanged(self):
        """Wrapped by an earlier version (no copy kept): the copy is made while the wrapper is
        exactly as it would be built, so a rename from then on stays. One that differs can't be
        told from an app's update: it gets none."""
        entry(self.flat / "org.notes.desktop", "/usr/bin/flatpak run org.notes @@u %U @@")
        entry(self.flat / "org.chat.desktop", "/usr/bin/flatpak run org.chat")
        self.launcher("--gate", "org.notes", "org.chat")
        for f in self.wl.BUILT_DIR.iterdir():
            f.unlink()                                                # (as an earlier version left them)
        chat = self.apps / "org.chat.desktop"
        chat.write_text(chat.read_text().replace("Name=App", "Name=Chat"))
        self.launcher("--list")
        self.assertTrue((self.wl.BUILT_DIR / "org.notes.desktop").exists())
        self.assertFalse((self.wl.BUILT_DIR / "org.chat.desktop").exists())
        notes = self.apps / "org.notes.desktop"
        notes.write_text(kde_saves(notes.read_text(), Name="My notes"))
        self.launcher("--gate", "org.notes")
        self.assertIn("Name=My notes", notes.read_text().splitlines())

    def test_environment_variables_you_give_it_go_after_the_gate(self):
        """KDE's menu editor writes them in front of the command (env VAR=… <the wrapper>): the gate
        still runs first, and a Flatpak keeps its way to the wallet."""
        entry(self.flat / "org.notes.desktop", "/usr/bin/flatpak run --branch=stable org.notes @@u %U @@")
        self.launcher("--gate", "org.notes")
        menu = self.apps / "org.notes.desktop"
        command = next(line[5:] for line in menu.read_text().splitlines() if line.startswith("Exec="))
        menu.write_text(kde_saves(menu.read_text(), Exec="env ELECTRON_OZONE_PLATFORM_HINT=wayland " + command))
        self.launcher("--gate", "org.notes")
        self.assertIn(f"Exec={self.wl.GATE} {self.wl.WRAPPER} env ELECTRON_OZONE_PLATFORM_HINT=wayland /usr/bin/flatpak "
                      "run --branch=stable --talk-name=org.kde.kwalletd6 --talk-name=org.freedesktop.secrets org.notes "
                      "@@u %U @@", menu.read_text().splitlines())
        self.launcher("--remove", "org.notes")
        self.assertIn("Exec=env ELECTRON_OZONE_PLATFORM_HINT=wayland /usr/bin/flatpak run --branch=stable org.notes "
                      "@@u %U @@", menu.read_text().splitlines())

    def test_your_edits_stay_when_the_protection_comes_off(self):
        # A Flatpak's entry: an override of the same name, with your edits, as KDE's menu editor saves one.
        entry(self.flat / "org.notes.desktop", "/usr/bin/flatpak run org.notes @@u %U @@")
        self.launcher("--gate", "org.notes")
        menu = self.apps / "org.notes.desktop"
        menu.write_text(kde_saves(menu.read_text(), Name="My notes"))
        self.launcher("--remove", "org.notes")
        text = menu.read_text()
        self.assertIn("Name=My notes", text.splitlines())
        self.assertIn("Exec=/usr/bin/flatpak run org.notes @@u %U @@", text.splitlines())
        self.assertNotIn("X-FrameTweaks-Wallet", text)
        self.assertFalse((self.wl.BUILT_DIR / "org.notes.desktop").exists())
        self.launcher("--gate", "org.notes")                          # (yours now: wrapped, and given back)
        self.launcher("--remove", "org.notes")
        self.assertEqual(menu.read_text(), text)
        # An app's own entry, kept while it's wrapped: back with your edits.
        own = self.apps / "my.app.desktop"
        entry(own, "/opt/app/run %U")
        self.launcher("--gate", "my.app")
        own.write_text(kde_saves(own.read_text(), Icon="my-icon"))
        self.launcher("--remove", "my.app")
        self.assertIn("Icon=my-icon", own.read_text().splitlines())
        self.assertIn("Exec=/opt/app/run %U", own.read_text().splitlines())
        self.assertFalse((self.orig / "my.app.desktop").exists())
        # Nothing changed: as before, the Flatpak's own entry shows again.
        entry(self.flat / "org.chat.desktop", "/usr/bin/flatpak run org.chat")
        self.launcher("--gate", "org.chat")
        self.launcher("--remove", "org.chat")
        self.assertFalse((self.apps / "org.chat.desktop").exists())


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


class Clocks:
    """app-timers' time module, in a test: the boot clock, and the monotonic one, which stands
    still while the Frame sleeps."""
    CLOCK_BOOTTIME = getattr(time, "CLOCK_BOOTTIME", 7)

    def __init__(self):
        self.boot = self.mono = 1000.0

    def clock_gettime(self, clock):
        assert clock == self.CLOCK_BOOTTIME
        return self.boot

    def monotonic(self):
        return self.mono

    def sleep(self, seconds):
        self.boot += seconds
        self.mono += seconds


def awake(seconds, press=False, headset=None):
    """One of the watcher's looks: seconds went by; a key was pressed; the proximity sensor reads
    20 (headset worn) or 3 (off)."""
    def look(clocks, press_key, sensor):
        clocks.sleep(seconds)
        if headset is not None:
            sensor(headset)
        if press:
            press_key()
    return look


def asleep(seconds, press=False, headset=None):
    """The Frame slept that long, then woke (by the key press or the headset, if given)."""
    def look(clocks, press_key, sensor):
        clocks.boot += seconds
        awake(0, press, headset)(clocks, press_key, sensor)
    return look


class TimersLoop(Home):
    """app-timers --run, look by look. Stand-ins: the clocks, an input device (a pipe), the
    headset's proximity sensor (a file), and quitting an app, which is only recorded (with when)."""
    def quits(self, looks, timers="org.notes = 15\n", sensor=True):
        at = load("app-timers", self.home)
        (self.home / "app-timers.conf").write_text(timers)
        prox = self.home / "in_proximity_raw"
        prox.write_text("3\n")
        r, w = os.pipe()
        clocks, quits, opened, looks = Clocks(), [], [], list(looks)
        real_open = os.open

        def select(rlist, wlist, xlist, timeout):
            if not looks:
                raise Done
            looks.pop(0)(clocks, lambda: os.write(w, struct.pack(at.EVENT, 0, 0, at.EV_KEY, 30, 1)),
                         lambda value: prox.write_text(f"{value}\n"))
            return select_module.select(rlist, wlist, xlist, 0)

        def open_(path, flags, *a):
            opened.append(real_open(path, flags, *a))
            return opened[-1]
        try:
            with mock.patch.multiple(at, CONF=self.home / "app-timers.conf", STATE=self.home / "app-timers.idle",
                                     PROX=[str(prox)] if sensor else [], input_devices=lambda: [f"/proc/self/fd/{r}"],
                                     select=types.SimpleNamespace(select=select), time=clocks, app_pids=lambda app: [4242],
                                     quit_app=lambda app, why: quits.append((app, why, clocks.boot)) or True), \
                    mock.patch("os.open", open_):
                with self.assertRaises(Done):
                    at.run()
        finally:
            for fd in (r, w, *opened):
                os.close(fd)
        return quits

    def test_a_night_asleep_counts_and_the_key_that_wakes_it_comes_after(self):
        # (the idle time stood still while the Frame slept, and the key that woke it reset it: the
        # app was still open in the morning, for whoever picked up the headset)
        night = 8 * 3600
        quits = self.quits([awake(2, press=True), awake(60), asleep(night, press=True), awake(2)], sensor=False)
        self.assertEqual(quits, [("org.notes", "No activity for 15 minutes.", 1000 + 62 + night)])

    def test_wearing_the_headset_is_activity(self):
        # The VR controllers aren't input devices: 20 minutes using only them, then the headset off.
        quits = self.quits([awake(60, headset=20) for _ in range(20)] + [awake(60, headset=3) for _ in range(16)])
        self.assertEqual(quits, [("org.notes", "No activity for 15 minutes.", 1000 + 20 * 60 + 15 * 60)])

    def test_the_headset_taken_off_just_before_it_sleeps(self):
        quits = self.quits([awake(2, headset=20), awake(2, headset=3), asleep(3600, press=True, headset=20), awake(2)],
                           timers="org.notes = 120 headset\n")
        self.assertEqual(quits, [("org.notes", "The headset was taken off.", 1004 + 3600)])

    def test_without_the_sensor_the_keyboard_and_mouse_count(self):
        quits = self.quits([awake(60, press=i == 0) for i in range(17)], sensor=False)
        self.assertEqual(quits, [("org.notes", "No activity for 15 minutes.", 1060 + 15 * 60)])


class OneDialog(Home):
    """Two unlock requests at once (Firefox started twice, a git push beside a gh call): one
    password dialog; the other waits for it and takes its answer, unlocked or cancelled."""
    def run_two(self, answer):
        wu = wallet_unlock(self.home)
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


class AutoLock(Home):
    """schedule_lock, with stand-ins for systemctl and systemd-run: one timer unit, loaded until
    it's stopped (another systemd-run with its name then fails), as systemd has it."""
    NOW, HOURS = 1_000_000, 4
    DEADLINE = NOW + HOURS * 3600

    def setUp(self):
        super().setUp()
        self.wu = wallet_unlock(self.home)
        self.timer, self.runs, self.both_stopped = [None], [], None
        guard = threading.Lock()

        def run(cmd, **kw):
            out, rc, err = "", 0, ""
            if cmd[0] == "systemd-run":
                with guard:
                    self.runs.append(cmd)
                    if self.timer[0] is not None:
                        rc, err = 1, "Failed to start transient timer unit: Unit wallet-autolock.timer was already loaded"
                    else:
                        at = [a.split("@", 1)[1] for a in cmd if a.startswith("--on-calendar=@")]
                        self.timer[0] = int(at[0]) if at else -1
            elif cmd[:3] == ["systemctl", "--user", "stop"]:
                with guard:
                    self.timer[0] = None
                if self.both_stopped:             # (the two at once: both stop the old timer first)
                    with contextlib.suppress(threading.BrokenBarrierError):
                        self.both_stopped.wait(0.5)
            elif cmd[:3] == ["systemctl", "--user", "show"] and self.timer[0] is not None:
                out = f"ActiveState=active\nTimersCalendar={{ OnCalendar=x ; next_elapse=@{self.timer[0]} }}\n"
            return subprocess.CompletedProcess(cmd, rc, out, err)
        for p in (mock.patch.object(self.wu, "subprocess", types.SimpleNamespace(run=run, DEVNULL=subprocess.DEVNULL)),
                  mock.patch.object(self.wu, "time", types.SimpleNamespace(time=lambda: float(self.NOW))),
                  mock.patch.dict(os.environ, {"WALLET_LOCK_HOURS": str(self.HOURS), "WALLET_AUTOLOCK": "1"})):
            p.start()
            self.addCleanup(p.stop)

    def test_it_locks_at_a_time_on_the_clock(self):
        # (a countdown, --on-active, started again at every daemon-reload and stood still while
        # the Frame slept: the wallet stayed unlocked hours past the time the page showed)
        self.assertEqual(self.wu.schedule_lock(), "4")
        self.assertEqual(len(self.runs), 1)
        self.assertIn(f"--on-calendar=@{self.DEADLINE}", self.runs[0])
        self.assertIn("--timer-property=AccuracySec=1s", self.runs[0])
        self.assertEqual([a for a in self.runs[0] if a.startswith("--on-active")], [])
        self.assertEqual(json.loads(self.wu.SESSION.read_text())["locks"], self.DEADLINE)     # what the page shows
        self.assertEqual(self.wu.timer_lock_time(), self.DEADLINE)                             # (--info, without it)

    def test_a_wallet_unlocked_in_another_ksecretd_is_another_unlock(self):
        """(a SteamVR restart ended the ksecretd it was unlocked in: the Wallet apps page counted
        "open for" from that unlock, hours before the one in use)"""
        self.wu.SESSION.write_text(json.dumps({"ksecretd": "100:5", "unlocked": 1.0, "locks": 2}))
        with mock.patch.object(self.wu, "ksecretd_id", lambda: "100:5"):
            self.wu.schedule_lock()                                # (the same one: an app reopening it)
        self.assertEqual(json.loads(self.wu.SESSION.read_text())["unlocked"], 1.0)
        self.timer[0] = None
        with mock.patch.object(self.wu, "ksecretd_id", lambda: "200:9"):
            self.wu.schedule_lock()
        s = json.loads(self.wu.SESSION.read_text())
        self.assertEqual((s["unlocked"], s["ksecretd"]), (self.NOW, "200:9"))

    def test_an_unlock_and_the_watcher_schedule_it_at_once(self):
        # (the second systemd-run found the first one's timer: "Wallet unlocked for ? hours")
        self.both_stopped = threading.Barrier(2)
        results = []
        with contextlib.redirect_stderr(io.StringIO()):
            both = [threading.Thread(target=lambda: results.append(self.wu.schedule_lock())) for _ in range(2)]
            for t in both:
                t.start()
            for t in both:
                t.join(10)
        self.assertEqual(results, ["4", "4"])
        self.assertEqual(self.timer[0], self.DEADLINE)
        self.assertEqual(json.loads(self.wu.SESSION.read_text())["locks"], self.DEADLINE)


class Watcher(Home):
    """wallet-unlock --watch, with a stand-in session bus."""
    def test_the_wallet_opened_while_it_locks_gets_its_auto_lock(self):
        # KWalletManager's Close, then an unlock right after, while the watcher is still locking it:
        # a blocking call drops what arrives meanwhile, so the open went unseen, with no auto-lock.
        wu = wallet_unlock(self.home)
        state, scheduled = {"locked": False}, []
        listening = FakeConn(ksecretd(state), [wallet_signal("walletClosed"), wallet_signal("walletOpened")])
        made = []

        def bus():
            made.append(FakeConn(ksecretd(state)) if made else listening)
            return made[-1]
        with mock.patch.dict(sys.modules, jeepney_stand_ins()), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.multiple(wu, bus=bus, broker=lambda: None, schedule_lock=lambda: scheduled.append(1) or "4"):
            with self.assertRaises(Done):
                wu.watch()
        self.assertTrue(state["locked"])           # the close became a lock in ksecretd
        self.assertEqual(scheduled, [1])           # and the open after it was seen


class FrontEnd(Home):
    """kwalletd6, what KWalletManager asks, kept in step with ksecretd: one started after an
    unlock said the wallet was closed while Firefox and Signal used it (it counts only what was
    opened through it)."""
    def bus(self, state):
        """Stand-in connections: kwalletd6 running unless state["kwalletd6"] is False, the wallet
        open there if state["front"], open in ksecretd unless state["locked"]; opens recorded."""
        def answer(message):
            kind, what = message
            if kind == "NameHasOwner":
                return (state.get(what.rsplit(".", 1)[1], True),)
            if what == "kwalletd6.isOpen":
                return (state.get("front", False),)
            if what == "kwalletd6.open":
                state["front"] = True
                state["opens"] += 1
                return (123,)
            if what == "isOpen":
                return (not state.get("locked"),)
            return ()
        made = []

        def bus():
            made.append(FakeConn(answer))
            return made[-1]
        return bus, made

    def test_it_opens_the_wallet_in_kwalletd6_only_when_kwalletd6_says_closed(self):
        wu = wallet_unlock(self.home)
        for state, opens in (({}, 1),                              # running, behind: opened there
                             ({"front": True}, 0),                 # in step already
                             ({"kwalletd6": False}, 0),            # not running: not started for this
                             ({"locked": True}, 0)):               # locked: nothing to show open
            state["opens"] = 0
            bus, made = self.bus(state)
            front = wu.FrontEnd()
            with mock.patch.object(wu, "bus", bus), contextlib.redirect_stdout(io.StringIO()):
                front.sync()
                front.sync()                                       # (once: then it's in step)
            self.assertEqual(state["opens"], opens, state)
            if opens:
                self.assertIs(front.conn, made[1])                 # (its handle's connection, kept)
                self.assertTrue(front.ours())

    def test_the_watcher_catches_kwalletd6_starting_and_its_own_open_isnt_an_apps(self):
        """KWalletManager starting kwalletd6 after the unlock: the watcher opens the wallet there,
        and the walletOpened that causes doesn't move the auto-lock; an app's later open does."""
        wu = wallet_unlock(self.home)
        state, scheduled = {"opens": 0, "kwalletd6": False}, []
        bus, made = self.bus(state)
        started = wallet_signal("NameOwnerChanged", ("org.kde.kwalletd6", "", ":1.9"))
        listening = FakeConn(lambda m: (), [started, wallet_signal("walletOpened")])

        def buses():
            if not made:
                made.append(listening)
                return listening
            return bus()
        received = listening.receive

        def receive(timeout=None):
            msg = received(timeout)
            if msg is started:
                state["kwalletd6"] = True
            return msg
        listening.receive = receive
        with mock.patch.dict(sys.modules, jeepney_stand_ins()), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.multiple(wu, bus=buses, broker=lambda: None, schedule_lock=lambda: scheduled.append(1) or "4"):
            with self.assertRaises(Done):
                wu.watch()
        self.assertEqual(state["opens"], 1)
        self.assertEqual(scheduled, [])                            # (our open: the lock stays put)
        self.assertIn({"type": "signal", "sender": "org.freedesktop.DBus", "interface": "org.freedesktop.DBus",
                       "member": "NameOwnerChanged", "path": "/org/freedesktop/DBus", "arg0": "org.kde.kwalletd6"},
                      [m[1] for m in listening.sent if m[0] == "AddMatch"])


class Broker(Home):
    """wallet-unlock's prompt broker (in --watch), with a stand-in session bus and windows."""
    def windows_listed(self, **state):
        wu = wallet_unlock(self.home)
        listed, looks = [], iter([None, None, Done()])           # two looks, then it stops

        def sleep(seconds):
            if isinstance(look := next(looks), Exception):
                raise look
        with mock.patch.multiple(wu, bus=lambda: FakeConn(ksecretd(state)),
                                 ksecretd_prompts=lambda: listed.append(1) or [],
                                 time=types.SimpleNamespace(sleep=sleep, strftime=time.strftime)):
            with self.assertRaises(Done):
                wu.broker()
        return len(listed)

    def test_windows_are_listed_only_while_the_wallet_is_locked(self):
        # (listing them, several programs every 1.5 s, took about 2.6% of a core all day)
        self.assertEqual(self.windows_listed(locked=False), 0)
        self.assertEqual(self.windows_listed(locked=True, running=False), 0)   # no ksecretd, no prompt
        self.assertEqual(self.windows_listed(locked=True), 2)

    def test_a_prompt_while_locked_is_closed_and_the_dialog_shown(self):
        wu = wallet_unlock(self.home)
        closed, started, naps = [], [], []

        def sleep(seconds):
            naps.append(seconds)
            if naps.count(1.5) > 1:                                # (one look)
                raise Done
        with mock.patch.multiple(wu, bus=lambda: FakeConn(ksecretd({"locked": True})),
                                 ksecretd_prompts=lambda: [(":0", 42)], x_env=lambda display: {"DISPLAY": display},
                                 close_window=lambda display, wid: closed.append((display, wid)),
                                 subprocess=types.SimpleNamespace(run=lambda cmd, env: started.append((cmd, env))),
                                 time=types.SimpleNamespace(sleep=sleep, strftime=time.strftime)), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Done):
                wu.broker()
        self.assertEqual(closed, [(":0", 42)])
        self.assertEqual(started, [([os.path.abspath(sys.argv[0])], {"DISPLAY": ":0", "QT_QPA_PLATFORM": "xcb"})])

    def test_a_one_pixel_window_isnt_a_prompt(self):
        # The dialog's check (prompt_pending) now uses the broker's rule: a 1-pixel window isn't one.
        wu = wallet_unlock(self.home)
        width = ["1"]

        def run(cmd, **kw):
            out = ""
            if cmd[:2] == ["xwininfo", "-root"]:
                out = '     0x2a00004 "KDE Wallet Service": ("ksecretd" "ksecretd")  400x200+0+0  +0+0\n'
            elif cmd[:2] == ["xwininfo", "-id"]:
                out = f"  Map State: IsViewable\n  Width: {width[0]}\n  Height: 1\n"
            return subprocess.CompletedProcess(cmd, 0, out, "")
        with mock.patch.object(wu, "subprocess", types.SimpleNamespace(run=run, SubprocessError=subprocess.SubprocessError)):
            self.assertFalse(wu.prompt_pending())
            width[0] = "400"
            self.assertTrue(wu.prompt_pending())


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

    def test_a_reinstall_keeps_every_apps_protection(self):
        """↻ on the wallet tweak: its install protects only its own three apps again, so the
        uninstall before it leaves the others' entries as they are."""
        self.tool(self.stubs, "systemctl", "exit 0")
        (self.bin / "wallet-launcher").write_bytes((WALLET / "wallet-launcher").read_bytes())
        (self.bin / "wallet-launcher").chmod(0o755)
        apps, orig = self.home / ".local/share/applications", self.home / ".local/share/frame-tweaks/launcher-originals"
        entry(orig / "org.mozilla.firefox.desktop", "/usr/bin/flatpak run org.mozilla.firefox %U")
        entry(apps / "org.mozilla.firefox.desktop", f"{self.bin}/wallet-gate /usr/bin/flatpak run org.mozilla.firefox %U",
              "X-FrameTweaks-Wallet=true")
        wrapped = (apps / "org.mozilla.firefox.desktop").read_text()
        env = sandbox_env(self.home, self.stubs, USER="test", FRAME_TWEAKS_REINSTALL="1")
        r = subprocess.run(["bash", str(WALLET / "uninstall.sh")], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((apps / "org.mozilla.firefox.desktop").read_text(), wrapped)
        self.assertTrue((orig / "org.mozilla.firefox.desktop").exists())

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

    def test_status_survives_a_failing_list(self):
        # (with pipefail and set -e, it stopped there: the wallet read as not installed)
        self.tool(self.stubs, "systemctl", "exit 0")
        self.tool(self.bin, "wallet-unlock", "echo locked")
        self.tool(self.bin, "wallet-launcher", "echo 'org.notes   shared gate'; exit 1")
        r = self.run_script("status.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("wallet locked; 1 app launcher(s)", r.stdout)

    def test_a_reinstall_keeps_a_menu_entrys_password(self):
        # ↻ on Dictation, password first on its entry: its uninstall (FRAME_TWEAKS_REINSTALL) kept
        # the entry but deleted the original kept beside it, so install_desktop wrote a plain one.
        self.tool(self.stubs, "systemctl", "exit 0")
        self.tool(self.stubs, "update-desktop-database", "exit 0")
        (self.bin / "wallet-launcher").write_bytes((WALLET / "wallet-launcher").read_bytes())
        (self.bin / "wallet-launcher").chmod(0o755)
        apps, kept = self.home / ".local/share/applications", self.home / ".local/share/frame-tweaks/launcher-originals"
        desktop = ROOT / "packs/core/dictation/dictate.desktop"

        def run(command, **env):
            r = subprocess.run(["bash", "-c", f'source "{ROOT}/lib/common.sh"; {command}'], capture_output=True,
                               text=True, timeout=60, env=sandbox_env(self.home, self.stubs, USER="test", **env))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        uninstall = f'bash "{ROOT}/packs/core/dictation/uninstall.sh"'
        run(f'install_desktop "{desktop}"')                       # Dictation installed,
        run('"$BIN/wallet-launcher" --gate --no-shared dictate')  # and Password first on the Wallet apps page
        run(uninstall, FRAME_TWEAKS_REINSTALL=1)
        run(f'install_desktop "{desktop}"')
        text = (apps / "dictate.desktop").read_text()
        self.assertIn(f"Exec={self.bin}/wallet-gate {self.bin}/dictate", text)
        self.assertIn("X-FrameTweaks-Wallet=true", text)
        run(uninstall)                                            # removing it still removes both
        self.assertFalse((apps / "dictate.desktop").exists())
        self.assertFalse((kept / "dictate.desktop").exists())

    def test_a_name_stays_through_protecting_and_unprotecting(self):
        """Dictation's entry renamed, then given Password first (the entry as written becomes the
        original: your name stays on top), updated, unprotected, and updated again."""
        self.tool(self.stubs, "systemctl", "exit 0")
        self.tool(self.stubs, "update-desktop-database", "exit 0")
        (self.bin / "wallet-launcher").write_bytes((WALLET / "wallet-launcher").read_bytes())
        (self.bin / "wallet-launcher").chmod(0o755)
        menu = self.home / ".local/share/applications/dictate.desktop"
        kept = self.home / ".local/share/frame-tweaks/launcher-originals/dictate.desktop"
        desktop = ROOT / "packs/core/dictation/dictate.desktop"

        def run(command):
            r = subprocess.run(["bash", "-c", f'source "{ROOT}/lib/common.sh"; {command}'], capture_output=True,
                               text=True, timeout=60, env=sandbox_env(self.home, self.stubs, USER="test"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        def says(*lines):
            for line in lines:
                self.assertIn(line, menu.read_text().splitlines())
        run(f'install_desktop "{desktop}"')
        menu.write_text(kde_saves(menu.read_text(), Name="Talk to type"))
        run('"$BIN/wallet-launcher" --gate --no-shared dictate')
        says("Name=Talk to type", f"Exec={self.bin}/wallet-gate {self.bin}/dictate")
        self.assertIn("Name=Dictate (toggle)", kept.read_text().splitlines())     # (the original, as written)
        run(f'install_desktop "{desktop}"')                                       # (an update)
        says("Name=Talk to type", f"Exec={self.bin}/wallet-gate {self.bin}/dictate")
        run('"$BIN/wallet-launcher" --remove dictate')
        says("Name=Talk to type", f"Exec={self.bin}/dictate")
        run(f'install_desktop "{desktop}"')
        says("Name=Talk to type", f"Exec={self.bin}/dictate")

    def test_a_name_you_gave_a_protected_entry_stays(self):
        """Dictation's entry, password first, renamed in KDE's menu editor: the name stays through a
        reinstall (↻) and a keyboard language change; uninstalling takes the copies kept for it."""
        self.tool(self.stubs, "systemctl", "exit 0")
        self.tool(self.stubs, "update-desktop-database", "exit 0")
        (self.bin / "wallet-launcher").write_bytes((WALLET / "wallet-launcher").read_bytes())
        (self.bin / "wallet-launcher").chmod(0o755)
        menu = self.home / ".local/share/applications/dictate.desktop"
        built = self.home / ".local/share/frame-tweaks/launcher-built/dictate.desktop"
        desktop = ROOT / "packs/core/dictation/dictate.desktop"

        def run(command, **env):
            r = subprocess.run(["bash", "-c", f'source "{ROOT}/lib/common.sh"; {command}'], capture_output=True,
                               text=True, timeout=60, env=sandbox_env(self.home, self.stubs, USER="test", **env))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        uninstall = f'bash "{ROOT}/packs/core/dictation/uninstall.sh"'
        run(f'install_desktop "{desktop}"')
        run('"$BIN/wallet-launcher" --gate --no-shared dictate')
        menu.write_text(kde_saves(menu.read_text(), Name="Talk to type"))
        run(uninstall, FRAME_TWEAKS_REINSTALL=1)
        run(f'install_desktop "{desktop}"')
        self.assertIn("Name=Talk to type", menu.read_text().splitlines())
        self.assertIn(f"Exec={self.bin}/wallet-gate {self.bin}/dictate", menu.read_text().splitlines())
        run(f'python3 "{ROOT}/lib/i18n.py" menus', FRAME_TWEAKS_LANGUAGE="es_419")    # (the keyboard's, now Spanish)
        lines = menu.read_text().splitlines()
        self.assertIn("Name=Talk to type", lines)
        self.assertIn("Comment=Inicia o detiene el dictado local con Whisper", lines)  # (ours: relabelled)
        self.assertTrue(built.exists())
        run(uninstall)
        self.assertFalse(menu.exists())
        self.assertFalse(built.exists())


class Gh(Home):
    """The gh wrapper and git's credential helper, as install.sh and uninstall.sh set them up and
    take them back: run from the installer window's Konsole, which has no Homebrew on its PATH.
    In a throwaway home and .gitconfig; gh itself is a stand-in that never runs."""
    def setUp(self):
        super().setUp()
        self.bin, self.stubs = self.home / ".local/bin", self.home / "stubs"
        for name, body in (("systemctl", "exit 0"), ("update-desktop-database", "exit 0"), ("notify-send", "exit 0"),
                           ("flatpak", '[ "$1" = info ] && exit 1; exit 0'), ("busctl", "exit 1"), ("qdbus6", "exit 0"),
                           ("kwriteconfig6", "exit 0"), ("kreadconfig6", "echo '<unset>'")):
            stub(self.stubs, name, body)
        stub(self.home / ".local/share/frame-tweaks/venv/bin", "python", "exit 0")   # (jeepney there: no pip)
        self.brew, self.ran = self.home / "brew", self.home / "gh-ran"
        stub(self.brew / "bin", "gh", f"touch {self.ran}")
        self.gitconfig = self.home / ".gitconfig"
        self.ours = f"!{self.bin}/gh auth git-credential"

    def tool(self, folder, name, body):
        stub(folder, name, body)

    def wallet(self, script, path=("/usr/bin", "/bin")):
        env = sandbox_env(self.home, self.stubs, [str(p) for p in path], USER="test", HOMEBREW_PREFIX=self.brew,
                          GIT_CONFIG_GLOBAL=self.gitconfig, GIT_CONFIG_NOSYSTEM=1)
        r = subprocess.run(["bash", str(WALLET / script)], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def helpers(self, host="https://github.com"):
        env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin", "GIT_CONFIG_GLOBAL": str(self.gitconfig),
               "GIT_CONFIG_NOSYSTEM": "1"}
        return subprocess.run(["git", "config", "--global", "--get-all", f"credential.{host}.helper"], env=env,
                              capture_output=True, text=True).stdout.splitlines()

    def test_from_the_window_and_back(self):
        # gh auth setup-git's helper, naming Homebrew's gh: the install found no gh (not on the
        # PATH), and the uninstall left the helper naming the wrapper it deleted.
        brew_gh = self.brew / "bin/gh"
        self.gitconfig.write_text(f'[credential "https://github.com"]\n\thelper =\n\thelper = !{brew_gh} auth git-credential\n')
        r = self.wallet("install.sh")
        real = shutil.which("gh", path="/usr/bin:/bin") or str(brew_gh)        # (one on the PATH first)
        self.assertIn(f'with-keyring" {real} "$@"', (self.bin / "gh").read_text())
        self.assertEqual(self.helpers(), ["", self.ours])
        self.assertNotIn("EMPTY password", r.stdout)            # (also said when you had set one)
        self.assertIn("If you haven't set one yet", r.stdout)
        self.wallet("uninstall.sh")
        self.assertFalse((self.bin / "gh").exists())
        self.assertEqual(self.helpers(), ["", f"!{real} auth git-credential"])
        self.assertFalse(self.ran.exists())

    def test_a_credential_helper_of_your_own_stays_the_only_one(self):
        # (--replace-all, matching no line, added the gh one beside it)
        self.gitconfig.write_text('[credential "https://github.com"]\n\thelper = store\n')
        self.wallet("install.sh", path=(self.brew / "bin", "/usr/bin", "/bin"))
        self.assertTrue((self.bin / "gh").exists())
        self.assertEqual(self.helpers(), ["store"])
        self.assertEqual(self.helpers("https://gist.github.com"), [])

    def test_uninstall_without_the_real_gh_takes_the_wrappers_helper_out(self):
        self.tool(self.bin, "gh", '# gh with its token in the shared KDE wallet (see with-keyring)\n'
                                  'exec "$HOME/.local/bin/with-keyring" /gone/gh "$@"')
        self.gitconfig.write_text(f'[credential "https://github.com"]\n\thelper =\n\thelper = {self.ours}\n'
                                  f'[credential "https://gist.github.com"]\n\thelper = store\n\thelper = {self.ours}\n')
        self.wallet("uninstall.sh")
        self.assertEqual(self.helpers(), [""])
        self.assertEqual(self.helpers("https://gist.github.com"), ["store"])
        self.assertFalse((self.bin / "gh").exists())

    def test_a_gh_of_your_own_stays(self):
        self.tool(self.bin, "gh", "echo mine")
        self.wallet("uninstall.sh")
        self.assertTrue((self.bin / "gh").exists())


if __name__ == "__main__":
    unittest.main()
