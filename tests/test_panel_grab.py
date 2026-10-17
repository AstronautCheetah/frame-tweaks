"""SteamVR's own grab bar under Frame Tweaks' VR panels while Steam's keyboard is open (the VR
environment helper's panel-grab patch): the panels' side (lib/vrkit.py DashboardGrab: where a
panel is, and what its bar did, through files), and sft-dashboard's, which relays them. Only
where a panel was let go reaches it: no controller pose."""
import json
import math
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "lib"))
from helpers import load_script  # noqa: E402
import vrkit  # noqa: E402

dash = load_script(ROOT / "packs/core/vr-dashboard" / "sft-dashboard", "sft_dashboard_grab")
POSE = vrkit.pose_of({"x": 0.4, "y": 1.6, "z": -0.9}, {"w": math.cos(0.4), "x": 0.0, "y": math.sin(0.4), "z": 0.0})


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name) / "panels"

    def test_where_it_is_and_what_the_bar_did(self):
        g = vrkit.DashboardGrab("frame-tweaks.test", self.dir)
        g.announce(POSE, 0.4, 0.2, True, "/run/user/1000/x.png")
        said = json.loads((self.dir / "frame-tweaks.test.json").read_text())
        self.assertEqual((said["pid"], said["w"], said["h"], said["visible"], said["picture"]),
                         (os.getpid(), 0.4, 0.2, True, "/run/user/1000/x.png"))
        self.assertEqual(said["t"], {"x": 0.4, "y": 1.6, "z": -0.9})
        self.assertIsNone(g.poll())                                     # (nothing from the bar yet)
        grab = self.dir / "frame-tweaks.test.grab.json"
        grab.write_text(json.dumps({"seq": 1, "state": "held"}))
        self.assertEqual(g.poll(), ("held", None))
        self.assertIsNone(g.poll())                                     # (once)
        grab.write_text(json.dumps({"seq": 2, "state": "dropped", "t": said["t"], "r": said["r"]}))
        kind, pose = g.poll()
        self.assertEqual(kind, "dropped")
        self.assertLess(max(abs(a - b) for ra, rb in zip(pose, POSE) for a, b in zip(ra, rb)), 1e-4)
        grab.write_text(json.dumps({"seq": 3, "state": "dropped"}))
        self.assertEqual(g.poll(), ("dropped", None))                   # (no place: where it was)
        g.close()
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_a_moving_panel_says_so_at_most_five_times_a_second(self):
        g = vrkit.DashboardGrab("frame-tweaks.test", self.dir)
        g.announce(POSE, 0.4, 0.2, True)
        moved = [row[:] for row in POSE]
        moved[0][3] += 0.1
        g.announce(moved, 0.4, 0.2, True)
        f = self.dir / "frame-tweaks.test.json"
        self.assertEqual(json.loads(f.read_text())["t"]["x"], 0.4)      # (waits)
        real = time.monotonic
        with mock.patch.object(vrkit.time, "monotonic", lambda: real() + 1):
            g.poll()
        self.assertEqual(json.loads(f.read_text())["t"]["x"], 0.5)      # (written by the next look)
        g.announce(POSE, 0.4, 0.2, True, now=True)
        self.assertEqual(json.loads(f.read_text())["t"]["x"], 0.4)      # (now: at once)

    def test_an_earlier_runs_bar_is_forgotten(self):
        self.dir.mkdir(parents=True)
        (self.dir / "frame-tweaks.test.grab.json").write_text(json.dumps({"seq": 9, "state": "held"}))
        g = vrkit.DashboardGrab("frame-tweaks.test", self.dir)
        self.assertIsNone(g.poll())

    def test_a_place_that_isnt_one(self):
        for t, r in (({"x": 1, "y": 2}, {"w": 1, "x": 0, "y": 0, "z": 0}),
                     ({"x": 1, "y": 2, "z": float("nan")}, {"w": 1, "x": 0, "y": 0, "z": 0}),
                     ({"x": 1, "y": 2, "z": 3}, {"w": 0, "x": 0, "y": 0, "z": 0}),
                     ({"x": 1e6, "y": 2, "z": 3}, {"w": 1, "x": 0, "y": 0, "z": 0})):
            self.assertIsNone(vrkit.pose_of(t, r), (t, r))


class Service(unittest.TestCase):
    """sft-dashboard: the panels to the page, the bar's doings to the panel."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.run_dir = Path(tmp.name)
        self.dir = self.run_dir / "frame-tweaks/panels"
        self.evals = []
        for p in (mock.patch.multiple(dash, PANELS=self.dir, RUN=self.run_dir),
                  mock.patch.object(dash, "ws_eval", lambda url, expr, timeout=5: self.evals.append(expr)),
                  mock.patch.object(dash, "systemui", lambda: "ws://page")):
            p.start()
            self.addCleanup(p.stop)
        self.picture = self.run_dir / "pad.png"
        self.picture.write_bytes(b"\x89PNG fake")
        self.g = vrkit.DashboardGrab("frame-tweaks.arrowpad", self.dir)
        self.g.announce(POSE, 0.4, 0.2, True, str(self.picture))

    def test_the_panels_whose_programs_run(self):
        self.assertEqual(set(dash.panels()), {"frame-tweaks.arrowpad"})
        gone = json.loads((self.dir / "frame-tweaks.arrowpad.json").read_text())
        gone["pid"] = 2 ** 22 + 12345                                   # (no such process)
        (self.dir / "frame-tweaks.gone.json").write_text(json.dumps(gone))
        (self.dir / "something-else.json").write_text("{}")
        self.assertEqual(set(dash.panels()), {"frame-tweaks.arrowpad"})
        self.assertEqual(dash.panels()["frame-tweaks.arrowpad"]["w"], 0.4)

    def test_held_then_let_go(self):
        dash.grab({"key": "frame-tweaks.arrowpad", "state": "held"})
        self.assertEqual(self.g.poll(), ("held", None))
        self.assertEqual(len(self.evals), 1)                            # its picture, for the page
        self.assertIn("data:image/png;base64,", self.evals[0])
        said = json.loads((self.dir / "frame-tweaks.arrowpad.json").read_text())
        dash.grab({"key": "frame-tweaks.arrowpad", "state": "dropped", "t": said["t"], "r": said["r"]})
        kind, pose = self.g.poll()
        self.assertEqual(kind, "dropped")
        self.assertAlmostEqual(pose[1][3], 1.6, places=4)

    def test_what_isnt_taken(self):
        for req in ({"key": "frame-tweaks.nobody", "state": "held"},           # (not announced)
                    {"key": "../../etc/x", "state": "held"},
                    {"key": "frame-tweaks.arrowpad", "state": "deleted"},
                    {"key": 5, "state": "held"}):
            dash.grab(req)
        self.assertIsNone(self.g.poll())
        dash.grab({"key": "frame-tweaks.arrowpad", "state": "dropped", "t": {"x": "a"}, "r": None})
        self.assertEqual(self.g.poll(), ("dropped", None))                   # (stays where it was)

    def test_only_a_picture_in_the_runtime_folder(self):
        other = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        self.addCleanup(os.unlink, other.name)
        self.g.announce(POSE, 0.4, 0.2, True, other.name, now=True)
        self.assertIsNone(dash.picture_url("frame-tweaks.arrowpad"))
        self.g.announce(POSE, 0.4, 0.2, True, str(self.run_dir / "notes.txt"), now=True)
        self.assertIsNone(dash.picture_url("frame-tweaks.arrowpad"))


class ArrowPad(unittest.TestCase):
    """The pad hides while SteamVR's bar holds it, and lands where its picture was let go."""

    def test_held_and_let_go(self):
        from test_vroverlay_math import load
        vo = load()
        o = vo.OverlayHost.__new__(vo.OverlayHost)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        o.dash_grab, o.dash_held = vrkit.DashboardGrab("frame-tweaks.arrowpad", Path(tmp.name)), False
        o.input_size, o.width_m, o.visible, o.pose = (500, 250), 0.5, True, [row[:] for row in POSE]
        o.input_handle, o.cover, o.drag, o.grip_drag = "pad", "cover", None, False
        o.ov = mock.Mock()
        calls = []
        for name in ("cancel_presses", "hide_note", "apply_pose", "remember_offset", "ease_level", "save", "reset_position"):
            setattr(o, name, lambda name=name: calls.append(name))
        o.log_input = lambda msg: None
        o.distance_from_head = lambda: 0.8
        o.dashboard_grab(True)
        said = json.loads((Path(tmp.name) / "frame-tweaks.arrowpad.json").read_text())
        self.assertEqual((said["w"], said["h"]), (0.5, 0.25))
        grab = Path(tmp.name) / "frame-tweaks.arrowpad.grab.json"
        grab.write_text(json.dumps({"seq": 1, "state": "held"}))
        o.dashboard_grab(True)
        self.assertTrue(o.dash_held)
        o.ov.hideOverlay.assert_any_call("pad")
        o.ov.hideOverlay.assert_any_call("cover")
        self.assertIn("cancel_presses", calls)
        t = {"x": 0.1, "y": 1.2, "z": -1.0}
        grab.write_text(json.dumps({"seq": 2, "state": "dropped", "t": t, "r": said["r"]}))
        o.dashboard_grab(True)
        self.assertFalse(o.dash_held)
        self.assertEqual([round(o.pose[i][3], 4) for i in range(3)], [0.1, 1.2, -1.0])
        self.assertEqual([c for c in calls if c != "cancel_presses" and c != "hide_note"],
                         ["apply_pose", "remember_offset", "ease_level", "save"])
        o.ov.showOverlay.assert_called_with("pad")
        self.assertEqual(json.loads((Path(tmp.name) / "frame-tweaks.arrowpad.json").read_text())["t"], t)


if __name__ == "__main__":
    unittest.main()
