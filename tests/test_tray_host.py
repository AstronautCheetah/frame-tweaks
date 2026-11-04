"""Tray icon crash fix (packs/bugfixes/tray-host): the tray watcher's bookkeeping (which item an app
registers, the list dropping apps that left), its status line, and, where this machine has
dbus-daemon and a system Python with PyGObject, the program itself on a private bus: registering,
the list, an app leaving, a name changing hands, a bad argument, and another program taking the
watcher's name and letting it go again. Background:
docs/research/tray-icon-flood.md. Run: python3 -m unittest -v"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script, sandbox_env, stub  # noqa: E402

TWEAK = ROOT / "packs/bugfixes/tray-host"
SCRIPT = TWEAK / "frame-tweaks-tray-host"
host = load_script(SCRIPT)          # (gi is imported only by main(): this needs none)


class ItemOf(unittest.TestCase):
    def test_a_bus_name_means_its_item_at_the_usual_path(self):
        # (what Qt 5's tray icon sends: its own service name)
        self.assertEqual(host.item_of("org.kde.StatusNotifierItem-4242-1", ":1.7"),
                         ("org.kde.StatusNotifierItem-4242-1", "org.kde.StatusNotifierItem-4242-1/StatusNotifierItem"))

    def test_a_unique_name(self):
        self.assertEqual(host.item_of(":1.31", ":1.7"), (":1.31", ":1.31/StatusNotifierItem"))

    def test_a_path_means_an_item_of_the_sender(self):
        self.assertEqual(host.item_of("/org/ayatana/NotificationItem/vlc", ":1.7"),
                         (":1.7", ":1.7/org/ayatana/NotificationItem/vlc"))

    def test_refused(self):
        for service in ("", "vlc", "org..kde", "org.kde.", "1org.kde", "/bad path", "/trailing/", "//", "org.kde.x" * 40):
            with self.subTest(service=service):
                self.assertIsNone(host.item_of(service, ":1.7"))
        self.assertIsNone(host.item_of("/ok", None))            # (a path, with no sender to own it)

    def test_never_crashes_only_rejects(self):
        # Anything an app could send: a result is always the sender's or the named bus's item.
        rng = random.Random(7)
        alphabet = "abc.:/-_1 é\0"
        for _ in range(5000):
            service = "".join(rng.choice(alphabet) for _ in range(rng.randrange(12)))
            found = host.item_of(service, ":1.7")
            if found is not None:
                bus, item = found
                self.assertTrue(host.valid_bus_name(bus))
                self.assertTrue(item.startswith(bus + "/"))
                self.assertEqual(bus, ":1.7" if service.startswith("/") else service)


class Items(unittest.TestCase):
    def test_once_each_in_order_and_gone_with_its_owner(self):
        items = host.Items()
        self.assertTrue(items.add("a.b", "a.b/StatusNotifierItem"))
        self.assertTrue(items.add(":1.9", ":1.9/x"))
        self.assertTrue(items.add(":1.9", ":1.9/y"))
        self.assertFalse(items.add("a.b", "a.b/StatusNotifierItem"))     # (registering again)
        self.assertEqual(items.ids(), ["a.b/StatusNotifierItem", ":1.9/x", ":1.9/y"])
        self.assertEqual(items.drop_owner(":1.9"), [":1.9/x", ":1.9/y"])
        self.assertEqual(items.drop_owner(":1.9"), [])
        self.assertEqual(items.ids(), ["a.b/StatusNotifierItem"])


# systemctl: is-active answers from ACTIVE (unit names, space-separated), is-enabled yes unless
# DISABLED, is-failed no unless FAILED; show -p MainPID prints MAINPID (which status.sh shouldn't
# need). busctl prints OWNER's pid, or fails without one.
SYSTEMCTL = r"""case " $* " in
    *" is-active "*) for u in $ACTIVE; do case " $* " in *" $u "*) exit 0 ;; esac; done; exit 3 ;;
    *" is-enabled "*) [ -z "${DISABLED:-}" ] ;;
    *" is-failed "*) [ -n "${FAILED:-}" ] ;;
    *" show "*) echo "${MAINPID:-0}" ;;
esac"""
BUSCTL = r"""[ -n "${OWNER:-}" ] || { echo "Failed: name has no owner" >&2; exit 1; }
echo "u $OWNER"
"""
SESSION = "gamescope-session.target"
BOTH = "gamescope-session.target frame-tweaks-tray-host.service"


class Status(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.stubs = self.home / "stubs"
        stub(self.stubs, "systemctl", SYSTEMCTL)
        stub(self.stubs, "busctl", BUSCTL)
        self.proc = self.home / "proc"
        # (pid 50: our service, as the user manager places it; 77: a program of the session)
        self.process(50, "frame-tweaks-tray", "0::/user.slice/user-1000.slice/user@1000.service/app.slice/frame-tweaks-tray-host.service")
        self.process(77, "kded6", "0::/user.slice/user-1000.slice/user@1000.service/app.slice/plasma-kded6.service")

    def process(self, pid, comm, cgroup):
        (self.proc / str(pid)).mkdir(parents=True)
        (self.proc / str(pid) / "comm").write_text(comm + "\n")
        (self.proc / str(pid) / "cgroup").write_text(cgroup + "\n")

    def install(self):
        (self.home / ".local/bin").mkdir(parents=True)
        prog = self.home / ".local/bin/frame-tweaks-tray-host"
        prog.write_text("#!/bin/true\n")
        prog.chmod(0o755)
        (self.home / ".config/systemd/user").mkdir(parents=True)
        (self.home / ".config/systemd/user/frame-tweaks-tray-host.service").write_text("[Unit]\n")

    def status(self, **env):
        r = subprocess.run(["bash", str(TWEAK / "status.sh")], capture_output=True, text=True, timeout=30,
                           env=sandbox_env(self.home, self.stubs, FRAME_TWEAKS_LIB=ROOT / "lib",
                                           FRAME_TWEAKS_PROC=self.proc, **env))
        return r.returncode, r.stdout.split(None, 1)[0], r.stdout

    def test_not_installed(self):
        self.assertEqual(self.status()[:2], (1, "missing"))

    def test_outside_the_vr_session(self):
        self.install()
        rc, word, out = self.status()
        self.assertEqual((rc, word), (0, "ok"))
        self.assertIn("starts with the VR session", out)

    def test_outside_the_vr_session_not_enabled(self):
        # (it wouldn't start with the session: not "starts with the VR session")
        self.install()
        rc, word, out = self.status(DISABLED=1)
        self.assertEqual((rc, word), (2, "warning"))
        self.assertIn("not enabled", out)

    def test_outside_the_vr_session_failed(self):
        self.install()
        rc, word, out = self.status(FAILED=1)
        self.assertEqual((rc, word), (2, "warning"))
        self.assertIn("service failed", out)

    def test_service_down(self):
        self.install()
        self.assertEqual(self.status(ACTIVE=SESSION)[:2], (2, "warning"))

    def test_running_without_the_name(self):
        self.install()
        rc, word, out = self.status(ACTIVE=BOTH, MAINPID=50)
        self.assertEqual((rc, word), (2, "warning"))
        self.assertIn("not answering", out)

    def test_answering(self):
        self.install()
        rc, word, out = self.status(ACTIVE=BOTH, MAINPID=50, OWNER=50)
        self.assertEqual((rc, word), (0, "ok"))
        self.assertIn("get an answer", out)

    def test_ours_by_its_cgroup_whatever_mainpid_says(self):
        # (MainPID read at another moment than the owner, a restart in between: still ours)
        self.install()
        rc, word, out = self.status(ACTIVE=BOTH, MAINPID=0, OWNER=50)
        self.assertEqual((rc, word), (0, "ok"))
        self.assertIn("get an answer", out)

    def test_another_program_has_the_name(self):
        self.install()
        rc, word, out = self.status(ACTIVE=BOTH, MAINPID=77, OWNER=77)
        self.assertEqual((rc, word), (0, "ok"))
        self.assertIn("another program answers tray icons in the VR session (kded6)", out)


class StartAgain(unittest.TestCase):
    """▶ Restart and a reinstall clear a failed unit's record first, so they start it whatever
    happened to it before (a start limit hit, say)."""

    def calls(self, script):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            stubs = home / "stubs"
            stub(stubs, "systemctl", 'echo "$*" >> "$HOME/calls"; case " $* " in *" is-active "*) exit 0 ;; esac')
            stub(stubs, "notify-send", "true")
            stub(stubs, "busctl", "exit 1")
            (home / ".local/bin").mkdir(parents=True)
            r = subprocess.run(["bash", str(TWEAK / script)], capture_output=True, text=True, timeout=60,
                               env=sandbox_env(home, stubs, FRAME_TWEAKS_LIB=ROOT / "lib"))
            self.assertEqual(r.returncode, 0, r.stderr)
            return [c.split()[1] for c in (home / "calls").read_text().splitlines()
                    if "frame-tweaks-tray-host.service" in c and c.split()[1] in ("reset-failed", "restart")]

    def test_restart_button(self):
        self.assertEqual(self.calls("run.sh"), ["reset-failed", "restart"])

    def test_install(self):
        self.assertEqual(self.calls("install.sh"), ["reset-failed", "restart"])


# The other side of the bus, in the system Python too (for gi): apps registering items on
# connections of their own, a reader of the list, and a program taking the watcher's name and
# letting it go again. Prints what it saw, as JSON.
CLIENT = r"""
import json, sys, time
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib
addr = sys.argv[1]
W, P = "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher"
def conn():
    return Gio.DBusConnection.new_for_address_sync(addr, Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
                                                   | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION, None, None)
def call(c, dest, path, iface, method, args, reply=None):
    return c.call_sync(dest, path, iface, method, args, reply and GLib.VariantType(reply), 0, 5000, None)
def bus(c, method, *args, sig="", reply=None):
    return call(c, "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", method,
                GLib.Variant(f"({sig})", args) if sig else None, reply).unpack()
def owner(c, name):
    try:
        return bus(c, "GetNameOwner", name, sig="s", reply="(s)")[0]
    except GLib.Error:
        return None
def items(c):
    return call(c, W, P, "org.freedesktop.DBus.Properties", "Get", GLib.Variant("(ss)", (W, "RegisteredStatusNotifierItems")), "(v)").unpack()[0]
def prop(c, name):
    return call(c, W, P, "org.freedesktop.DBus.Properties", "Get", GLib.Variant("(ss)", (W, name)), "(v)").unpack()[0]
def register(c, service):
    call(c, W, P, W, "RegisterStatusNotifierItem", GLib.Variant("(s)", (service,)))
def until(test):
    for _ in range(100):
        if test():
            return True
        time.sleep(0.05)
    return False
out = {}
reader = conn()
out["up"] = until(lambda: owner(reader, W))
watcher = owner(reader, W)
out["host"], out["version"] = prop(reader, "IsStatusNotifierHostRegistered"), prop(reader, "ProtocolVersion")

# An app: an item by its service name (twice: listed once), and one by a path.
app = conn()
bus(app, "RequestName", "org.kde.StatusNotifierItem-1-1", 4, sig="su", reply="(u)")
register(app, "org.kde.StatusNotifierItem-1-1")
register(app, "org.kde.StatusNotifierItem-1-1")
register(app, "/org/test/Item")
out["app"] = app.get_unique_name()
out["items"] = items(reader)
try:
    register(app, "not a name")
    out["bad"] = "accepted"
except GLib.Error as e:
    out["bad"] = Gio.DBusError.get_remote_error(e)
# A name nobody owns: answered, never listed.
register(reader, "org.example.NobodyOwnsThis")
out["unowned_listed"] = "org.example.NobodyOwnsThis/StatusNotifierItem" in items(reader)
app.close_sync(None)
out["after_quit"] = until(lambda: items(reader) == [])

# A name that changes hands while its first owner stays on the bus: the item goes with the owner.
first, second = conn(), conn()
bus(first, "RequestName", "org.kde.StatusNotifierItem-2-1", 4, sig="su", reply="(u)")
register(first, "org.kde.StatusNotifierItem-2-1")
out["handed_listed"] = items(reader) == ["org.kde.StatusNotifierItem-2-1/StatusNotifierItem"]
out["queued"] = bus(second, "RequestName", "org.kde.StatusNotifierItem-2-1", 0, sig="su", reply="(u)")[0]
bus(first, "ReleaseName", "org.kde.StatusNotifierItem-2-1", sig="s", reply="(u)")
out["handed_dropped"] = until(lambda: items(reader) == [])
first.close_sync(None)
second.close_sync(None)

# Another program takes the name (replacement allowed), then quits: the watcher owns it again.
other = conn()
out["took_over"] = bus(other, "RequestName", W, 2, sig="su", reply="(u)")[0]
out["other_owns"] = owner(reader, W) == other.get_unique_name()
other.close_sync(None)
out["back"] = until(lambda: owner(reader, W) == watcher)
print(json.dumps(out))
"""


def system_gi():
    try:
        return subprocess.run(["/usr/bin/python3", "-c", "import gi; gi.require_version('Gio', '2.0'); from gi.repository import Gio"],
                              capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def stop(p):
    if p.poll() is None:
        p.kill()
    p.wait(timeout=10)


@unittest.skipUnless(shutil.which("dbus-daemon") and system_gi(), "needs dbus-daemon and /usr/bin/python3 with PyGObject")
class OnABus(unittest.TestCase):
    def test_answers_tracks_and_waits_its_turn(self):
        with tempfile.TemporaryDirectory() as d:
            addr = f"unix:path={d}/bus"
            daemon = subprocess.Popen(["dbus-daemon", "--session", "--nofork", f"--address={addr}"],
                                      stdout=subprocess.DEVNULL)
            self.addCleanup(stop, daemon)
            for _ in range(100):
                if Path(f"{d}/bus").exists():
                    break
                time.sleep(0.05)
            self.assertTrue(Path(f"{d}/bus").exists(), "dbus-daemon didn't start")
            env = {**os.environ, "DBUS_SESSION_BUS_ADDRESS": addr}
            with open(f"{d}/log", "w") as log:
                watcher = subprocess.Popen(["/usr/bin/python3", str(SCRIPT)], env=env, stdout=log, stderr=subprocess.STDOUT)
            self.addCleanup(stop, watcher)
            client = subprocess.run(["/usr/bin/python3", "-c", CLIENT, addr], capture_output=True, text=True, timeout=60)
            self.assertEqual(client.returncode, 0, client.stderr)
            seen = json.loads(client.stdout)
            app = seen["app"]
            self.assertTrue(seen["up"])
            self.assertEqual((seen["host"], seen["version"]), (True, 0))
            self.assertEqual(seen["items"], ["org.kde.StatusNotifierItem-1-1/StatusNotifierItem", f"{app}/org/test/Item"])
            self.assertEqual(seen["bad"], "org.freedesktop.DBus.Error.InvalidArgs")
            self.assertFalse(seen["unowned_listed"])
            self.assertTrue(seen["after_quit"])
            self.assertTrue(seen["handed_listed"])
            self.assertEqual(seen["queued"], 2)          # (in the queue behind the first owner)
            self.assertTrue(seen["handed_dropped"])
            self.assertEqual(seen["took_over"], 1)       # (primary owner: replacement allowed)
            self.assertTrue(seen["other_owns"])
            self.assertTrue(seen["back"])                # (queued, not gone)
            self.assertIsNone(watcher.poll())
            text = Path(f"{d}/log").read_text()
            self.assertIn("is another program's for now", text)
            self.assertIn(f"item gone: {app}/org/test/Item", text)


if __name__ == "__main__":
    unittest.main()


class Needed(unittest.TestCase):
    """Offered only where the VR session sets KDE's Qt theme (what makes tray icons flood the bus):
    elsewhere the window hides it and ./install.sh install skips it."""

    def needed(self, text):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "gamescope-session"
            if text is not None:
                f.write_text(text)
            return subprocess.run(["bash", str(TWEAK / "needed.sh")], capture_output=True, text=True,
                                  env={**os.environ, "HOME": d, "FRAME_TWEAKS_GAMESCOPE_SESSION": str(f)})

    def test_needed_where_the_session_sets_the_kde_theme(self):
        r = self.needed("#!/bin/bash\n# Make Qt apps use the styling\nexport QT_QPA_PLATFORMTHEME=kde\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_not_needed_without_it(self):
        for text in ("#!/bin/bash\nexport XCURSOR_THEME=steam\n", "# export QT_QPA_PLATFORMTHEME=kde (once)\n", None):
            with self.subTest(text):
                r = self.needed(text)
                self.assertEqual(r.returncode, 1)
                self.assertIn("KDE's Qt theme", r.stdout)
