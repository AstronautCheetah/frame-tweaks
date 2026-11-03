"""lib/vrbindings.py: SteamVR controller bindings patched for tweaks and put back, against a stand-in
for SteamVR's binding API (an HTTP server in a thread, answering as SteamVR did on a Frame)."""
import json
import os
import random
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import ROOT, sandbox_env  # noqa: E402
import vrbindings  # noqa: E402

APP, CTRL = vrbindings.APP, vrbindings.CONTROLLER
DEFAULT = "file:///opt/steamvr/drivers/frame_controller/resources/input/vrcompositor_bindings_frame_controller.json"
OTHER = "file:///home/user/.steam/steam/config/my_bindings.json"


def system_source(hand, **inputs):
    return {"path": f"/user/hand/{hand}/input/system", "mode": "button",
            "inputs": {k: {"output": v} for k, v in inputs.items()}}


# The parts of the Frame's own dashboard binding the tests touch (as SteamVR loaded it).
BINDING = {
    "app_key": APP, "controller_type": CTRL, "name": "Default VR Dashboard bindings for Steam Frame Controller",
    "bindings": {
        "/actions/quickrecenter": {"sources": [
            system_source("left", long="/actions/quickrecenter/in/Recenter"),
            system_source("right", long="/actions/quickrecenter/in/Recenter")]},
        "/actions/system": {"sources": [
            system_source("right", click="/actions/system/in/ToggleDashboard",
                          double="/actions/system/in/ToggleRoomView"),
        ], "chords": [{"inputs": [["/user/hand/right/input/system", "held"],
                                  ["/user/hand/right/input/trigger", "click"]],
                       "output": "/actions/system/in/TakeScreenshot"}]},
    },
}
NO_RECENTER_RIGHT = {"edits": [{"op": "remove", "action_set": "/actions/quickrecenter",
                                "path": "/user/hand/right/input/system", "input": "long"}]}
NO_RECENTER_LEFT = {"edits": [{"op": "remove", "action_set": "/actions/quickrecenter",
                               "path": "/user/hand/left/input/system", "input": "long"}]}


class FakeSteamVR:
    """SteamVR's binding API: which binding each (app, controller) uses, the bindings it ships
    (in memory) and any file:// binding on disk. Without SteamVR's page as Origin: 401, as SteamVR."""

    def __init__(self):
        self.current = {(APP, CTRL): DEFAULT, (APP, "knuckles"): "file:///opt/k.json"}
        self.shipped = {DEFAULT: BINDING, OTHER: dict(BINDING, name="mine"), "file:///opt/k.json": BINDING}
        self.selects, self.refuse_select = [], False
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def answer(self, data, code=200):
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.headers.get("Origin") != fake.base:
                    return self.answer({}, 401)
                u = urllib.parse.urlparse(self.path)
                q = dict(urllib.parse.parse_qsl(u.query))
                if u.path == "/input/getactions.json":
                    urls = {c: url for (a, c), url in fake.current.items() if a == q["app_key"]}
                    return self.answer({"current_binding_url": urls, "jsonid": "vr_input_get_actions"})
                if u.path == "/input/loadbindingfromurl.json":
                    url = q["binding_url"]
                    config = fake.shipped.get(url)
                    if config is None and url.startswith("file://"):
                        try:
                            config = json.loads(Path(urllib.parse.unquote(url[7:])).read_text())
                        except (OSError, ValueError):
                            config = None
                    if config is None:
                        return self.answer({"success": False, "uri": url})
                    return self.answer({"success": "True", "binding_config": config, "uri": url})
                self.answer({}, 404)

            def do_POST(self):
                if self.headers.get("Origin") != fake.base:
                    return self.answer({}, 401)
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/input/selectconfig.action" and not fake.refuse_select:
                    fake.selects.append(body["url"])
                    fake.current[(body["app_key"], body["controller_type"])] = body["url"]
                    return self.answer({"success": True})
                self.answer({"success": False})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def binding(self, controller=CTRL):
        url = self.current[(APP, controller)]
        return self.shipped.get(url) or json.loads(Path(urllib.parse.unquote(url[7:])).read_text())


def recenter_paths(config):
    return [s["path"] for s in config["bindings"]["/actions/quickrecenter"]["sources"]]


class Bindings(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        env = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        self.vr = FakeSteamVR()
        self.addCleanup(self.vr.stop)
        self.api = vrbindings.SteamVR(self.vr.base)

    def patch(self, name, edit):
        return vrbindings.patch(name, vrbindings.parse_edit(edit), api=self.api)

    def state(self):
        return vrbindings.read_state()["slots"]

    def test_show_names_the_binding_and_sums_it_up(self):
        url, config = vrbindings.show(api=self.api)
        self.assertEqual(url, DEFAULT)
        text = "\n".join(vrbindings.summary(config))
        self.assertIn("/user/hand/right/input/system (button): long → Recenter", text)
        self.assertIn("click → ToggleDashboard, double → ToggleRoomView", text)
        self.assertIn("chord /user/hand/right/input/system held + /user/hand/right/input/trigger click → TakeScreenshot", text)

    def test_patch_selects_a_copy_and_records_what_it_replaced(self):
        msg = self.patch("dictation", NO_RECENTER_RIGHT)
        self.assertIn("patched", msg)
        active = self.vr.current[(APP, CTRL)]
        self.assertTrue(active.startswith((self.home / ".local/share/frame-tweaks/bindings").as_uri()), active)
        config = self.vr.binding()
        self.assertEqual(recenter_paths(config), ["/user/hand/left/input/system"])
        self.assertEqual(config["bindings"]["/actions/system"], BINDING["bindings"]["/actions/system"])
        self.assertIn("(Frame Tweaks: dictation)", config["name"])
        slot = self.state()[f"{APP}|{CTRL}"]
        self.assertEqual(slot["original_url"], DEFAULT)
        self.assertEqual(slot["original_hash"], vrbindings.digest(BINDING))
        self.assertEqual(list(slot["patches"]), ["dictation"])
        self.assertEqual(Path(slot["file"]).as_uri(), active)
        self.assertEqual(recenter_paths(BINDING), ["/user/hand/left/input/system", "/user/hand/right/input/system"])

        self.assertIn("already active", self.patch("dictation", NO_RECENTER_RIGHT))
        self.assertEqual(len(self.vr.selects), 1)                   # (a reinstall selects nothing)
        self.assertEqual(vrbindings.status(api=self.api), [("dictation", APP, CTRL, True)])

    def test_restore_selects_the_original_and_forgets(self):
        self.patch("dictation", NO_RECENTER_RIGHT)
        f = Path(self.state()[f"{APP}|{CTRL}"]["file"])
        self.assertIn("restored", vrbindings.restore("dictation", api=self.api))
        self.assertEqual(self.vr.current[(APP, CTRL)], DEFAULT)
        self.assertFalse(f.exists())
        self.assertEqual(self.state(), {})
        self.assertIn("no such patch", vrbindings.restore("dictation", api=self.api))
        self.assertEqual(vrbindings.status(api=self.api), [])

    def test_a_binding_chosen_since_stays(self):
        self.patch("dictation", NO_RECENTER_RIGHT)
        f = Path(self.state()[f"{APP}|{CTRL}"]["file"])
        self.vr.current[(APP, CTRL)] = OTHER                         # (chosen in SteamVR's settings)
        self.assertEqual(vrbindings.status(api=self.api), [("dictation", APP, CTRL, False)])
        with self.assertRaisesRegex(vrbindings.BindingsError, "changed since"):
            self.patch("other-tweak", NO_RECENTER_LEFT)
        self.assertIn("left as it is", vrbindings.restore("dictation", api=self.api))
        self.assertEqual(self.vr.current[(APP, CTRL)], OTHER)
        self.assertEqual(self.state(), {})
        self.assertFalse(f.exists())

    def test_a_copy_changed_since_is_left_alone(self):
        self.patch("dictation", NO_RECENTER_RIGHT)
        f = Path(self.state()[f"{APP}|{CTRL}"]["file"])
        config = json.loads(f.read_text())
        config["bindings"]["/actions/quickrecenter"]["sources"] = []
        f.write_text(json.dumps(config))                             # (someone edited it by hand)
        self.assertIn("left as it is", vrbindings.restore("dictation", api=self.api))
        self.assertEqual(self.vr.current[(APP, CTRL)], f.as_uri())
        self.assertTrue(f.exists())                                  # (SteamVR still uses it)
        self.assertEqual(self.vr.selects, [f.as_uri()])

    def test_two_patches_stack_and_restore_separately(self):
        self.patch("a", NO_RECENTER_RIGHT)
        self.patch("b", NO_RECENTER_LEFT)
        self.assertEqual(recenter_paths(self.vr.binding()), [])
        self.assertIn("(Frame Tweaks: a, b)", self.vr.binding()["name"])
        self.assertEqual(sorted(r[0] for r in vrbindings.status(api=self.api)), ["a", "b"])
        files = list((self.home / ".local/share/frame-tweaks/bindings").glob("*.json"))
        self.assertEqual(len(files), 1)                              # (the copy before b's is gone)

        vrbindings.restore("a", api=self.api)
        self.assertEqual(recenter_paths(self.vr.binding()), ["/user/hand/right/input/system"])
        self.assertEqual(list(self.state()[f"{APP}|{CTRL}"]["patches"]), ["b"])
        vrbindings.restore("b", api=self.api)
        self.assertEqual(self.vr.current[(APP, CTRL)], DEFAULT)
        self.assertEqual(list((self.home / ".local/share/frame-tweaks/bindings").glob("*")), [])

    def test_a_name_patches_one_binding_only(self):
        self.patch("a", NO_RECENTER_RIGHT)
        with self.assertRaisesRegex(vrbindings.BindingsError, "another binding"):
            self.patch("a", dict(NO_RECENTER_RIGHT, controller="knuckles"))
        self.patch("b", dict(NO_RECENTER_RIGHT, controller="knuckles"))   # (another slot: its own copy)
        self.assertEqual(len(self.state()), 2)

    def test_set_changes_or_adds_a_source(self):
        edit = {"edits": [
            {"op": "set", "action_set": "/actions/system", "path": "/user/hand/right/input/system",
             "input": "long", "output": "/actions/system/in/ToggleRoomView"},
            {"op": "set", "action_set": "/actions/system", "path": "/user/hand/left/input/system",
             "mode": "button", "input": "click", "output": "/actions/system/in/ToggleDashboard"}]}
        self.patch("s", edit)
        sources = self.vr.binding()["bindings"]["/actions/system"]["sources"]
        self.assertEqual(sources[0]["inputs"]["long"], {"output": "/actions/system/in/ToggleRoomView"})
        self.assertEqual(sources[0]["inputs"]["click"], {"output": "/actions/system/in/ToggleDashboard"})
        self.assertEqual(sources[1], system_source("left", click="/actions/system/in/ToggleDashboard"))
        no_mode = {k: v for k, v in edit["edits"][1].items() if k != "mode"}
        with self.assertRaisesRegex(ValueError, "mode"):             # (a new source needs one)
            vrbindings.apply_edits(BINDING, [no_mode])

    def test_remove_only_where_the_output_matches(self):
        edit = dict(NO_RECENTER_RIGHT["edits"][0], output="/actions/quickrecenter/in/Other")
        self.assertIn("nothing to change", self.patch("x", {"edits": [edit]}))
        self.assertEqual(self.vr.selects, [])
        self.assertEqual(self.state(), {})

    def test_steamvr_not_running_changes_nothing(self):
        self.vr.stop()
        with self.assertRaisesRegex(vrbindings.NotRunning, "isn't running"):
            self.patch("dictation", NO_RECENTER_RIGHT)
        self.assertFalse((self.home / ".local/share/frame-tweaks/bindings").exists())
        self.assertEqual(self.state(), {})
        self.assertEqual(vrbindings.status(api=self.api), [])

    def test_restore_while_steamvr_is_off_keeps_the_record(self):
        self.patch("dictation", NO_RECENTER_RIGHT)
        self.vr.stop()
        self.assertEqual(vrbindings.status(api=self.api), [("dictation", APP, CTRL, None)])
        with self.assertRaises(vrbindings.NotRunning):
            vrbindings.restore("dictation", api=self.api)
        slot = self.state()[f"{APP}|{CTRL}"]
        self.assertTrue(Path(slot["file"]).exists())                 # (SteamVR loads it at its start)

    def test_a_refused_select_leaves_no_copy(self):
        self.vr.refuse_select = True
        with self.assertRaisesRegex(vrbindings.BindingsError, "didn't select"):
            self.patch("dictation", NO_RECENTER_RIGHT)
        self.assertEqual(list((self.home / ".local/share/frame-tweaks/bindings").glob("*")), [])
        self.assertEqual(self.state(), {})
        self.assertEqual(self.vr.current[(APP, CTRL)], DEFAULT)

    def test_without_steamvrs_origin_the_api_refuses(self):
        api = vrbindings.SteamVR(self.vr.base)
        api.base = self.vr.base.replace("127.0.0.1", "localhost")    # (its Origin no longer SteamVR's page)
        with self.assertRaisesRegex(vrbindings.BindingsError, "401"):
            api.current_url(APP, CTRL)

    def test_the_command_line(self):
        edit = self.home / "edit.json"
        edit.write_text(json.dumps(NO_RECENTER_RIGHT))
        env = sandbox_env(self.home, FRAME_TWEAKS_VRINPUT_URL=self.vr.base)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        def run(*args):
            return subprocess.run([sys.executable, str(ROOT / "lib/vrbindings.py"), *args], env=env,
                                  capture_output=True, text=True, timeout=30)

        r = run("show")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith(DEFAULT + "\n"), r.stdout)
        r = run("patch", "dictation", str(edit))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(run("status").stdout, r"^dictation: .*frame_controller: active$")
        self.assertEqual(json.loads(run("show", "--json").stdout)["name"].split(" (")[-1], "Frame Tweaks: dictation)")
        self.assertEqual(run("restore", "dictation").returncode, 0)
        self.assertIn("No SteamVR binding patches", run("status").stdout)
        edit.write_text('{"edits": [{"op": "drop"}]}')
        r = run("patch", "dictation", str(edit))
        self.assertEqual(r.returncode, 2)
        self.assertIn("op", r.stderr)
        self.assertEqual(run("patch", "Bad Name", str(self.home / "edit.json")).returncode, 2)
        self.vr.stop()
        edit.write_text(json.dumps(NO_RECENTER_RIGHT))
        r = run("patch", "dictation", str(edit))
        self.assertEqual(r.returncode, 1)
        self.assertIn("SteamVR isn't running", r.stderr)


class EditFile(unittest.TestCase):
    def test_defaults_and_strictness(self):
        got = vrbindings.parse_edit(NO_RECENTER_RIGHT)
        self.assertEqual((got["app"], got["controller"]), (APP, CTRL))
        for bad in ([], {"edits": []}, {"edits": [{}]}, dict(NO_RECENTER_RIGHT, extra=1),
                    {"edits": [dict(NO_RECENTER_RIGHT["edits"][0], mode="button")]},   # (mode: set only)
                    {"edits": [dict(NO_RECENTER_RIGHT["edits"][0], path="system")]},
                    {"edits": [{"op": "set", "action_set": "/actions/x", "path": "/user/x", "input": "click"}]},
                    dict(NO_RECENTER_RIGHT, app="../x")):
            with self.assertRaises(ValueError, msg=bad):
                vrbindings.parse_edit(bad)

    def test_random_input_is_rejected_never_crashes(self):
        """Any JSON value: parse_edit returns an edit or raises ValueError; what it returns,
        apply_edits takes without crashing (a set that needs a mode may raise ValueError)."""
        rng = random.Random(20261103)
        atoms = [None, True, 0, 1.5, "", "x", "remove", "set", "/actions/system", "/user/hand/right/input/system",
                 "long", "button", "app", "edits", "op", "action_set", "path", "input", "output", "mode"]

        def value(depth=0):
            r = rng.random()
            if depth > 3 or r < 0.4:
                return rng.choice(atoms)
            if r < 0.6:
                return [value(depth + 1) for _ in range(rng.randrange(4))]
            keys = rng.sample(atoms[4:], rng.randrange(1, 7))
            return {k: value(depth + 1) for k in keys}

        def edit_like():
            def mostly(good, *bad):
                return rng.choice(bad) if rng.random() < 0.1 else rng.choice(good)
            e = {"op": mostly(["remove", "set"], "x"), "action_set": mostly(["/actions/system", "/actions/new"], 3),
                 "path": mostly(["/user/hand/right/input/system", "/user/x"], ""), "input": mostly(["long", "click"], None)}
            for k in ("output", "mode") + (("extra",) if rng.random() < 0.1 else ()):
                if rng.random() < 0.6:
                    e[k] = mostly(["/actions/system/in/X", "button"], "", 7)
            return e

        accepted = 0
        for _ in range(3000):
            data = value() if rng.random() < 0.5 else {"edits": [edit_like() for _ in range(rng.randrange(1, 4))]}
            try:
                got = vrbindings.parse_edit(data)
            except ValueError:
                continue
            accepted += 1
            try:
                out = vrbindings.apply_edits(BINDING, got["edits"])
            except ValueError:
                continue
            self.assertIsInstance(out, dict)
            json.dumps(out)
        self.assertGreater(accepted, 50)                             # (the generator reaches valid files)


if __name__ == "__main__":
    unittest.main()
