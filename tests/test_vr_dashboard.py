"""vr-dashboard/sft-dashboard: settings arm/restore, each patch's SteamVR compatibility check, the
service's bindings and restarts; install.sh / uninstall.sh in a throwaway home."""
import sys
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script, sandbox_env, stub  # noqa: E402
sft = load_script(ROOT / "packs/original/vr-dashboard" / "sft-dashboard", "sft")
def _patches():
    """Every dashboard patch a tweak installs: install_dashboard_patch NAME FILE in its install.sh."""
    found = {}
    for inst in ROOT.glob("packs/*/*/install.sh"):
        for name, rel in re.findall(r'install_dashboard_patch\s+(\S+)\s+"\$TWEAK_DIR/([^"]+)"', inst.read_text()):
            found[name] = inst.parent / rel
    return found


PATCHES = _patches()
PATCHES_AND_LIB = {**PATCHES, "lib": ROOT / "packs/original/vr-dashboard" / "lib.js"}


class ArmRestore(unittest.TestCase):
    def run_case(self, before):
        with tempfile.TemporaryDirectory() as d:
            settings, state = Path(d) / "steamvr.vrsettings", Path(d) / "state" / "prev"
            settings.write_text(json.dumps(before))
            with mock.patch.object(sft, "SETTINGS", settings), mock.patch.object(sft, "STATE", state):
                sft.arm()
                self.assertIs(json.loads(settings.read_text())["VRWebHelper"]["DebuggerEnabled"], True)
                sft.arm()                                   # twice: still restores the original
                sft.restore()
                self.assertFalse(state.exists())
                return json.loads(settings.read_text())

    def test_absent_key_is_removed_again(self):
        self.assertEqual(self.run_case({"steamvr": {"a": 1}}), {"steamvr": {"a": 1}})

    def test_false_is_put_back(self):
        after = self.run_case({"VRWebHelper": {"DebuggerEnabled": False, "x": 1}})
        self.assertEqual(after, {"VRWebHelper": {"DebuggerEnabled": False, "x": 1}})

    def test_true_by_user_is_left_alone(self):
        self.assertEqual(self.run_case({"VRWebHelper": {"DebuggerEnabled": True}}),
                         {"VRWebHelper": {"DebuggerEnabled": True}})

    def test_unreadable_note_still_turns_the_port_off(self):
        """A note of the previous value cut short (a crash just after arm) mustn't leave the port on."""
        for note in ("", "fal", "\x00\x00"):
            with tempfile.TemporaryDirectory() as d:
                settings, state = Path(d) / "steamvr.vrsettings", Path(d) / "prev"
                settings.write_text(json.dumps({"VRWebHelper": {"DebuggerEnabled": True, "x": 1}}))
                state.write_text(note)
                with mock.patch.object(sft, "SETTINGS", settings), mock.patch.object(sft, "STATE", state):
                    sft.restore()
                self.assertEqual(json.loads(settings.read_text()), {"VRWebHelper": {"x": 1}}, repr(note))
                self.assertFalse(state.exists())


class DashboardCheck(unittest.TestCase):
    def test_every_patch_is_found(self):
        self.assertGreaterEqual(set(PATCHES), {"curvature", "float-return", "float-grab", "scroll-strips",
                                               "phone-rotate", "phone-touch"})
        for path in PATCHES.values():
            self.assertTrue(path.is_file(), path)

    def test_each_patch_detects_missing_markers(self):
        for name, path in PATCHES_AND_LIB.items():
            req = sft.requires(path)
            self.assertGreater(len(req), 2, name)                  # its own "// requires:" lines
            self.assertEqual(sft.missing(path, "".join(req.values())), [], name)
            self.assertEqual(sorted(sft.missing(path, "nothing here")), sorted(req), name)
            self.assertEqual(sft.missing(path, None), ["SteamVR's dashboard files"])

    def test_no_dashboard_files(self):
        """SteamVR's dashboard folder gone (or moved by an update): said so, every patch off."""
        with tempfile.TemporaryDirectory() as d, mock.patch.object(sft, "DASHBOARD", Path(d) / "gone"):
            code = sft.dashboard_code()
        self.assertIsNone(code)
        self.assertEqual(sft.missing(PATCHES["curvature"], code), ["SteamVR's dashboard files"])

    def test_patch_that_isnt_utf8(self):
        """A patch with a stray byte (a pack's, saved in another encoding) is still checked."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "p.js"
            p.write_bytes(b"// caf\xe9\n// requires: a thing | thing(\n(() => 'patched')()\n")
            self.assertEqual(sft.missing(p, "window.FrameStore= thing("), [])
            self.assertEqual(sft.missing(p, "window.FrameStore="), ["a thing"])

    @unittest.skipUnless(sft.DASHBOARD.is_dir(), "SteamVR isn't installed here")
    def test_patches_match_the_installed_steamvr(self):
        code = sft.dashboard_code()
        for name, path in PATCHES_AND_LIB.items():
            self.assertEqual(sft.missing(path, code), [], name)


class SaveConfig(unittest.TestCase):
    def test_only_installed_patches_and_small_objects(self):
        with tempfile.TemporaryDirectory() as d:
            conf = Path(d) / "conf"
            with mock.patch.object(sft, "CONF_DIR", conf), \
                 mock.patch.object(sft, "patches", return_value={"scroll-strips": Path("x.js")}):
                sft.save_config({"name": "scroll-strips", "config": {"color": 0.5}})
                self.assertEqual(json.loads((conf / "scroll-strips.json").read_text()), {"color": 0.5})
                sft.save_config({"name": "../evil", "config": {"a": 1}})
                sft.save_config({"name": "other", "config": {"a": 1}})
                sft.save_config({"name": "scroll-strips", "config": ["not", "an", "object"]})
                sft.save_config({"name": "scroll-strips", "config": {"big": "x" * 5000}})
                self.assertEqual(sorted(p.name for p in conf.iterdir()), ["scroll-strips.json"])
                self.assertEqual(json.loads((conf / "scroll-strips.json").read_text()), {"color": 0.5})


class Stop(BaseException):
    """Ends one of the service's endless loops in a test (time.sleep raises it)."""


def _called(name, payload):
    return {"method": "Runtime.bindingCalled", "params": {"name": name, "payload": payload}}


class Bindings(unittest.TestCase):
    def test_bad_calls_dont_end_the_listening(self):
        """Any script on the page can call the bindings with anything; the thread must go on."""
        calls = [_called("sftConfig", "null"), _called("sftScroll", "[1]"), _called("sftScroll", '{"dx": 1e999}'),
                 _called("sftConfig", json.dumps({"name": "scroll-strips", "config": {"color": 0.5}}))]

        class Page:                                  # the dashboard page's DevTools connection
            def __init__(self, url, timeout=None):
                pass

            def send(self, obj):
                pass

            def recv(self):
                if calls:
                    return calls.pop(0)
                raise OSError("closed")              # (then: wait and connect again)

        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(sft, "CONF_DIR", Path(d)), \
                mock.patch.object(sft, "patches", return_value={"scroll-strips": Path("x.js")}), \
                mock.patch.object(sft, "systemui", return_value="ws://127.0.0.1:1/devtools/page/1"), \
                mock.patch.object(sft, "Ws", Page), mock.patch.object(sft, "keys") as keys, \
                mock.patch.object(sft.time, "sleep", side_effect=Stop), \
                mock.patch("builtins.print"):
            with self.assertRaises(Stop):
                sft.listen()
            self.assertEqual(json.loads((Path(d) / "scroll-strips.json").read_text()), {"color": 0.5})
        keys.assert_not_called()


class Watch(unittest.TestCase):
    def test_restarted_service_stops_a_removed_patch(self):
        """A tweak removed just before the service restarted (an install right after restarts it):
        its patch, still on the page, is stopped all the same."""
        page = {"curvature": "patched", "scroll-strips": "patched"}       # what's running on the page
        evaluated = []

        def ws_eval(url, expr, timeout=5):
            evaluated.append(expr)
            if expr == "Object.keys(window.__sftPatches ?? {})":
                return list(page)
            for n in list(page):
                if expr == sft.stop_expr(n):
                    del page[n]
                    return "stopped"
            return "already patched"

        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "patches").mkdir()
            (Path(d) / "patches" / "scroll-strips.js").write_text("// requires: a thing | thing(\n")
            (Path(d) / "lib.js").write_text("// requires: another | other(\n")
            with mock.patch.object(sft, "PATCHES", Path(d) / "patches"), mock.patch.object(sft, "LIB", Path(d) / "lib.js"), \
                    mock.patch.object(sft, "CHECK_FILE", Path(d) / "status"), mock.patch.object(sft, "CONF_DIR", Path(d)), \
                    mock.patch.object(sft, "dashboard_code", return_value="window.FrameStore= thing( other("), \
                    mock.patch.object(sft.threading, "Thread"), \
                    mock.patch.object(sft, "systemui", return_value="ws://127.0.0.1:1/devtools/page/1"), \
                    mock.patch.object(sft, "ws_eval", ws_eval), mock.patch.object(sft, "i18n_expr", return_value="1"), \
                    mock.patch.object(sft.time, "sleep", side_effect=Stop), mock.patch("builtins.print"):
                with self.assertRaises(Stop):
                    sft.watch()
        self.assertEqual(page, {"scroll-strips": "patched"})
        self.assertIn(sft.stop_expr("curvature"), evaluated)
        self.assertNotIn(sft.stop_expr("scroll-strips"), evaluated)


class Scripts(unittest.TestCase):
    """install.sh and uninstall.sh in a throwaway home, with stand-ins for systemctl (STEAMVR: 0
    while SteamVR runs), timeout (sft-dashboard status) and the unpatching python3: nothing here
    reaches SteamVR's real port."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.log = self.home / "calls.log"
        (self.home / "stubs").mkdir()
        self.stub("systemctl", f'echo "systemctl $*" >> "{self.log}"\n'
                  '[ "$2" = is-active ] && { [ "$4" = steamvr.service ] && exit "${STEAMVR:-3}"; exit 3; }; exit 0')
        self.stub("timeout", 'echo "port closed (SteamVR not running, or not restarted since install)"; exit 2')
        self.stub("python3", f'[ "$1" = - ] && {{ echo unpatch >> "{self.log}"; cat > /dev/null; exit 0; }}\n'
                  'exec /usr/bin/python3 "$@"')

    def stub(self, name, body):
        stub(self.home / "stubs", name, body)

    def run_script(self, script, steamvr=3):
        env = sandbox_env(self.home, self.home / "stubs", STEAMVR=steamvr)
        r = subprocess.run(["bash", str(ROOT / "packs/original/vr-dashboard" / script)], env=env,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_installed_while_steamvr_runs_without_the_port(self):
        """status exits 2 with "port closed": the restart-SteamVR message, not "active" (pipefail)."""
        out = self.run_script("install.sh", steamvr=0)
        self.assertIn("starts working the next time SteamVR starts", out)
        self.assertNotIn("restart sft-dashboard.service", self.log.read_text())

    def test_install_clears_the_uninstalls_restore_copy(self):
        """A reinstall while SteamVR ran: the uninstall's own restore step is replaced, so its copy goes."""
        left = self.home / ".local/state/frame-tweaks/sft-dashboard-restore"
        left.parent.mkdir(parents=True)
        left.write_text("#!/bin/sh\n")
        self.run_script("install.sh")
        self.assertFalse(left.exists())

    def test_unpatches_only_while_steamvr_runs(self):
        """(A test's throwaway home, as here, must never unpatch the real dashboard.)"""
        for steamvr, unpatched in ((3, False), (0, True)):
            self.log.write_text("")
            self.run_script("install.sh")
            self.run_script("uninstall.sh", steamvr)
            self.assertEqual("unpatch" in self.log.read_text().split(), unpatched, steamvr)


if __name__ == "__main__":
    unittest.main()
