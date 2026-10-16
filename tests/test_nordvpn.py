"""NordVPN's "Connect at startup": nordvpn-wg autoconnect turns NetworkManager's autoconnect on for
one location and off for the others, without connecting it there and then; a refresh, which makes
the connections anew, keeps it; removing that location turns it off; list and status say which.
Against a stand-in NetworkManager (nmcli and the D-Bus calls, through a stand-in jeepney), so the
real connections are never touched. Then the tray's menu item: its location, tick, and command."""
import copy
import io
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, load_script  # noqa: E402

PACK = ROOT / "packs/integrations/nordvpn"
SETTINGS = "/org/freedesktop/NetworkManager/Settings"
BLOCK = 0x20


class FakeNM:
    """NetworkManager as nordvpn-wg reaches it. Like the real one, it connects a connection that
    autoconnects as soon as it's added or changed, unless the call blocks that (flag 0x20); and
    a connection's settings come without its private key, which an update that leaves it out keeps."""

    def __init__(self, codes, active=None, auto=()):
        self.cons, self.calls, self.refuse = {}, [], False
        for code, name in codes.items():
            self.add(self.settings(name, code, code in auto), "key", active=code == active)

    @staticmethod
    def settings(name, code, auto):
        return {"connection": {"id": ("s", name), "type": ("s", "wireguard"),
                               "interface-name": ("s", "nordvpn-" + code.lower()), "autoconnect": ("b", auto)},
                "wireguard": {"peers": ("aa{sv}", [{"public-key": ("s", "pub-" + code)}])},
                "ipv4": {"method": ("s", "manual"), "dns-priority": ("i", -50)}}

    def add(self, settings, key, active=False):
        name = settings["connection"]["id"][1]
        uuid = f"uuid-{len(self.calls)}-{name}"
        settings["connection"]["uuid"] = ("s", uuid)
        self.cons[name] = {"settings": settings, "key": key, "active": active, "uuid": uuid}

    def auto(self, name):
        return self.cons[name]["settings"]["connection"]["autoconnect"][1]

    def on(self):
        """{name: autoconnect}"""
        return {n: self.auto(n) for n in self.cons}

    def active(self):
        return sorted(n for n, c in self.cons.items() if c["active"])

    # -- nmcli
    def nmcli(self, *args, check=True):
        self.calls.append(("nmcli",) + args)
        a, esc = list(args), lambda n: n.replace(":", "\\:")
        if a == ["-t", "-f", "NAME,TYPE", "connection", "show"]:
            return "Home:802-11-wireless\n" + "".join(f"{esc(n)}:wireguard\n" for n in self.cons)
        if a == ["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"]:
            return "Home:wlan0\n" + "".join(f"{esc(n)}:{c['settings']['connection']['interface-name'][1]}\n"
                                            for n, c in self.cons.items() if c["active"])
        if a == ["-t", "-f", "AUTOCONNECT,TYPE,NAME", "connection", "show"]:
            return "yes:802-11-wireless:Home\n" + "".join(
                f"{'yes' if self.auto(n) else 'no'}:wireguard:{esc(n)}\n" for n in self.cons)
        if a[:2] == ["-g", "connection.interface-name"]:
            return self.cons[a[-1]]["settings"]["connection"]["interface-name"][1] + "\n"
        if a[:2] == ["-g", "connection.uuid"]:
            return self.cons[a[-1]]["uuid"] + "\n"
        if a[:2] == ["connection", "delete"]:
            del self.cons[a[2]]
            return ""
        if a[:2] == ["connection", "up"]:
            self.cons[a[2]]["active"] = True
            return "Connection successfully activated\n"
        raise AssertionError(f"nmcli {args}: not expected")

    # -- D-Bus (the stand-in jeepney's connection)
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send_and_get_reply(self, msg):
        addr, method, signature, body = msg
        reply = lambda *b: types.SimpleNamespace(header=types.SimpleNamespace(message_type="return"), body=b)
        if self.refuse:
            return types.SimpleNamespace(header=types.SimpleNamespace(message_type="error"), body=("Not allowed",))
        if method == "AddConnection2":
            assert (addr.object_path, addr.interface, signature) == (SETTINGS, "org.freedesktop.NetworkManager.Settings", "a{sa{sv}}ua{sv}")
            settings, flags, _args = copy.deepcopy(body)
            key = settings["wireguard"].pop("private-key")[1]
            auto = settings["connection"]["autoconnect"][1]
            self.add(settings, key, active=auto and not flags & BLOCK)
            self.calls.append(("AddConnection2", settings["connection"]["id"][1], auto, flags))
            return reply(SETTINGS + "/9")
        if method == "GetConnectionByUuid":
            assert (addr.object_path, signature) == (SETTINGS, "s")
            return reply(next(f"{SETTINGS}/{n}" for n, c in self.cons.items() if c["uuid"] == body[0]))
        name = addr.object_path[len(SETTINGS) + 1:]
        assert addr.interface == "org.freedesktop.NetworkManager.Settings.Connection", addr.interface
        con = self.cons[name]
        if method == "GetSettings":
            return reply(copy.deepcopy(con["settings"]))
        if method == "Update2":
            settings, flags, _args = body
            assert signature == "a{sa{sv}}ua{sv}"
            assert "private-key" not in settings["wireguard"]     # (NetworkManager keeps the one it has)
            old, new = copy.deepcopy(con["settings"]), copy.deepcopy(settings)
            auto = new["connection"].pop("autoconnect")[1]
            old["connection"].pop("autoconnect")
            assert new == old, "Update2 changed more than autoconnect"
            con["settings"]["connection"]["autoconnect"] = ("b", auto)
            con["active"] = con["active"] or (auto and not flags & BLOCK)
            self.calls.append(("Update2", name, auto, flags))
            return reply({})
        raise AssertionError(f"D-Bus {method}: not expected")

    def jeepney(self):
        """Stand-in jeepney modules, whose system bus is this NetworkManager."""
        j = types.ModuleType("jeepney")
        j.DBusAddress = lambda object_path, bus_name=None, interface=None: types.SimpleNamespace(
            object_path=object_path, bus_name=bus_name, interface=interface)
        j.MessageType = types.SimpleNamespace(error="error", method_return="return")
        j.new_method_call = lambda addr, method, signature=None, body=(): (addr, method, signature, body)
        blocking = types.ModuleType("jeepney.io.blocking")
        blocking.open_dbus_connection = lambda bus="SESSION": (self if bus == "SYSTEM" else None)
        return {"jeepney": j, "jeepney.io": types.ModuleType("jeepney.io"), "jeepney.io.blocking": blocking}

    def changes(self):
        """The D-Bus writes made: (method, name, autoconnect, flags)."""
        return [c for c in self.calls if c[0] in ("AddConnection2", "Update2")]


COUNTRIES = {"US": "United States", "CA": "Canada", "JP": "Japan"}


class Autoconnect(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch.dict(os.environ, {"HOME": tmp.name}):
            self.wg = load_script(PACK / "nordvpn-wg")
        conf = Path(tmp.name) / ".config/nordvpn-wg"
        conf.mkdir(parents=True)
        for name in ("CONF", "KEY", "LOCATIONS", "SERVERS", "STARTUP"):     # (into the throwaway home)
            setattr(self.wg, name, conf / getattr(self.wg, name).name)
        self.wg.KEY.write_text("key\n")
        self.wg.save_locations(list(COUNTRIES))

    def nm(self, active=None, auto=()):
        self.fake = FakeNM({c: f"NordVPN {n}" for c, n in COUNTRIES.items()}, active, auto)
        for p in (mock.patch.object(self.wg, "nmcli", self.fake.nmcli),
                  mock.patch.dict(sys.modules, self.fake.jeepney()),
                  mock.patch.object(self.wg, "countries", lambda: {c: {"id": i, "name": n} for i, (c, n) in enumerate(COUNTRIES.items())}),
                  mock.patch.object(self.wg, "best_server", lambda cid: (f"srv{cid}.nordvpn.com", f"10.0.0.{cid}", "pub", "City", 9))):
            p.start()
            self.addCleanup(p.stop)
        return self.fake

    def run_wg(self, *args):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["nordvpn-wg", *args]), redirect_stdout(out):
            self.wg.main()
        return out.getvalue()

    def choice(self):
        return self.wg.STARTUP.read_text().strip() if self.wg.STARTUP.exists() else None

    def test_one_location_connects_at_startup_and_no_other(self):
        nm = self.nm(active="US", auto=["JP"])        # (Japan's set by hand, say)
        out = self.run_wg("autoconnect", "ca")
        self.assertEqual(out, "NordVPN Canada connects at startup.\n")
        self.assertEqual(nm.on(), {"NordVPN United States": False, "NordVPN Canada": True, "NordVPN Japan": False})
        self.assertEqual(self.choice(), "CA")
        # the other off first; Canada isn't connected now (blocked: 0x20), only from the next start
        self.assertEqual(nm.changes(), [("Update2", "NordVPN Japan", False, 0x1), ("Update2", "NordVPN Canada", True, 0x21)])
        self.assertEqual(nm.active(), ["NordVPN United States"])

    def test_the_connected_location_stays_connected_unblocked(self):
        nm = self.nm(active="US")
        self.run_wg("autoconnect", "US")
        self.assertEqual(nm.changes(), [("Update2", "NordVPN United States", True, 0x1)])   # (not blocked: it reconnects if it drops)
        self.assertEqual(nm.active(), ["NordVPN United States"])

    def test_already_so_changes_nothing(self):
        nm = self.nm(auto=["CA"])
        self.assertEqual(self.run_wg("autoconnect", "CA"), "NordVPN Canada connects at startup.\n")
        self.assertEqual(nm.changes(), [])
        self.assertEqual(self.choice(), "CA")

    def test_off(self):
        nm = self.nm(auto=["CA"])
        self.wg.save_startup_choice("CA")
        self.assertEqual(self.run_wg("autoconnect", "off"), "No NordVPN location connects at startup.\n")
        self.assertEqual(nm.on(), dict.fromkeys(nm.cons, False))
        self.assertIsNone(self.choice())
        self.assertEqual(nm.active(), [])

    def test_without_a_location_it_says_which(self):
        self.nm(auto=["JP"])
        self.assertEqual(self.run_wg("autoconnect"), "NordVPN Japan connects at startup.\n")
        self.nm()
        self.assertEqual(self.run_wg("autoconnect"), "No NordVPN location connects at startup.\n")

    def test_a_location_not_set_up_is_refused(self):
        nm = self.nm(auto=["CA"])
        with self.assertRaises(SystemExit) as e:
            self.run_wg("autoconnect", "DE")
        self.assertIn("DE isn't configured", str(e.exception.code))
        self.assertEqual(nm.changes(), [])
        self.assertTrue(nm.auto("NordVPN Canada"))

    def test_networkmanager_refusing_says_so(self):
        nm = self.nm()
        nm.refuse = True
        with self.assertRaises(SystemExit) as e:
            self.run_wg("autoconnect", "CA")
        self.assertIn("NetworkManager refused the change", str(e.exception.code))
        self.assertIsNone(self.choice())

    def test_refresh_keeps_the_choice(self):
        nm = self.nm(active="US", auto=["CA"])
        self.wg.save_startup_choice("CA")
        self.run_wg("refresh")
        self.assertEqual(nm.on(), {"NordVPN United States": False, "NordVPN Canada": True, "NordVPN Japan": False})
        self.assertIn(("AddConnection2", "NordVPN Canada", True, 0x21), nm.changes())     # (blocked: not now)
        self.assertIn(("AddConnection2", "NordVPN Japan", False, 0x1), nm.changes())
        self.assertEqual(nm.active(), ["NordVPN United States"])             # (reconnected, and only it)
        self.assertEqual({c["key"] for c in nm.cons.values()}, {"key"})

    def test_refresh_reconnects_the_startup_location_if_it_was_connected(self):
        nm = self.nm(active="CA", auto=["CA"])
        self.wg.save_startup_choice("CA")
        self.run_wg("refresh")
        self.assertTrue(nm.auto("NordVPN Canada"))
        self.assertEqual(nm.active(), ["NordVPN Canada"])
        self.assertIn(("nmcli", "connection", "up", "NordVPN Canada"), nm.calls)

    def test_removing_the_startup_location_turns_it_off(self):
        nm = self.nm(auto=["CA"])
        self.wg.save_startup_choice("CA")
        out = self.run_wg("remove", "CA")
        self.assertEqual(out, "removed CA\nNo NordVPN location connects at startup.\n")
        self.assertNotIn("NordVPN Canada", nm.cons)
        self.assertIsNone(self.choice())
        self.run_wg("add", "CA")                       # (back as a location, not as the startup one)
        self.assertFalse(nm.auto("NordVPN Canada"))

    def test_removing_another_location_keeps_it(self):
        self.nm(auto=["CA"])
        self.wg.save_startup_choice("CA")
        self.assertEqual(self.run_wg("remove", "JP"), "removed JP\n")
        self.assertEqual(self.choice(), "CA")

    def test_list_and_status_say_which(self):
        self.nm(active="US", auto=["CA"])
        lines = self.run_wg("list").splitlines()
        self.assertEqual([line.endswith("(connects at startup)") for line in lines], [False, True, False])
        self.assertTrue(lines[0].startswith("● US  NordVPN United States"))
        with mock.patch("urllib.request.urlopen", side_effect=OSError("offline")):
            self.assertEqual(self.run_wg("status"), "NordVPN: connected via NordVPN United States\n"
                                                    "NordVPN Canada connects at startup.\n")
        self.nm()
        self.assertEqual(self.run_wg("status"), "NordVPN: disconnected\n")


class TrayItem(unittest.TestCase):
    """The tray's "Connect at startup (…)": ticked for the one that does; otherwise it names the
    connected one, else the one used last, else the first; ticking and unticking run nordvpn-wg."""

    @classmethod
    def setUpClass(cls):
        with mock.patch.dict(os.environ, {"QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}):
            cls.tray = load_script(PACK / "nordvpn-tray")
            from PyQt6.QtWidgets import QApplication, QMenu
            cls.app = QApplication.instance() or QApplication([])
        cls.QMenu = QMenu

    def connections(self, lines):
        done = types.SimpleNamespace(stdout="".join(line + "\n" for line in lines))
        with mock.patch.object(self.tray.subprocess, "run", return_value=done) as run:
            got = self.tray.nm_connections()
        self.assertEqual(run.call_args.args[0][:4], ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE,AUTOCONNECT,TIMESTAMP"])
        return got

    def test_reads_startup_and_last_used(self):
        got = self.connections(["Home:802-11-wireless:wlan0:yes:1792000000",
                                "NordVPN United States:wireguard:nordvpn-us:no:1792120242",
                                "NordVPN Canada:wireguard::yes:0",
                                "NordVPN Japan:wireguard::no:1792130000"])
        self.assertEqual(got, (["NordVPN Canada", "NordVPN Japan", "NordVPN United States"],
                               "NordVPN United States", "NordVPN Canada", "NordVPN Japan"))
        got = self.connections(["NordVPN Canada:wireguard::no:0", "NordVPN Japan:wireguard::no:0"])
        self.assertEqual(got, (["NordVPN Canada", "NordVPN Japan"], None, None, None))   # (all made anew: none used yet)

    def item(self, active=None, startup=None, last=None):
        t = self.tray.Tray.__new__(self.tray.Tray)      # (no icon in a real tray, no Plasma panel asked)
        t.app, t.menu, t.ran = mock.Mock(), self.QMenu(), []
        t.profiles = ["NordVPN Canada", "NordVPN Japan", "NordVPN United States"]
        t.active, t.startup, t.last = active, startup, last
        t._codes = {"NordVPN Canada": "CA", "NordVPN Japan": "JP", "NordVPN United States": "US"}
        t.run = lambda *args, note=None: t.ran.append(args)
        t.build_menu()
        items = [a for a in t.menu.actions() if a.text().startswith("Connect at startup")]
        self.assertEqual(len(items), 1)
        return items[0], t.ran

    def test_ticked_for_the_one_that_connects_at_startup(self):
        a, ran = self.item(active="NordVPN United States", startup="NordVPN Canada")
        self.assertEqual((a.text(), a.isCheckable(), a.isChecked()), ("Connect at startup (Canada)", True, True))
        a.trigger()                                     # unticked: off
        self.assertEqual(ran, [("autoconnect", "off")])

    def test_unticked_it_names_the_connected_one(self):
        a, ran = self.item(active="NordVPN United States", last="NordVPN Japan")
        self.assertEqual((a.text(), a.isChecked()), ("Connect at startup (United States)", False))
        a.trigger()
        self.assertEqual(ran, [("autoconnect", "US")])

    def test_disconnected_it_names_the_one_used_last_else_the_first(self):
        self.assertEqual(self.item(last="NordVPN Japan")[0].text(), "Connect at startup (Japan)")
        self.assertEqual(self.item()[0].text(), "Connect at startup (Canada)")

    def test_no_locations_no_item(self):
        t = self.tray.Tray.__new__(self.tray.Tray)
        t.app, t.menu, t.profiles, t._codes = mock.Mock(), self.QMenu(), [], {}
        t.active = t.startup = t.last = None
        t.build_menu()
        self.assertFalse([a for a in t.menu.actions() if a.text().startswith("Connect at startup")])


if __name__ == "__main__":
    unittest.main()
