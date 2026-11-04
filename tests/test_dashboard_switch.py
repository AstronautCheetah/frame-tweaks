"""The Turn off / Turn on button of Curved world windows, Back to the previous window and Pick up
when floating: run.sh flips "enabled" in the patch's settings file (lib/common.sh
dashboard_patch_switch), run-label.sh and status.sh follow it, and each patch, run in Node with a
fake dashboard, does nothing while window.__sftPatchConfig[NAME].enabled is false.

What only the headset shows: that the watcher's 5 s look delivers the setting to the running
dashboard, and that the dashboard then behaves as stock."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script, sandbox_env, stub  # noqa: E402

TWEAKS = ("curvature", "float-return", "float-grab")


class Button(unittest.TestCase):
    """The scripts in a throwaway home, the patch file put where install_dashboard_patch puts it,
    SteamVR not running (systemctl's stand-in), notify-send logged."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.stubs = self.home / "stubs"
        self.log = self.home / "notify.log"
        stub(self.stubs, "systemctl", "exit 3")
        stub(self.stubs, "notify-send", f'printf "%s|%s\\n" "$3" "$4" >> "{self.log}"')

    def run_script(self, tweak, script, **env):
        r = subprocess.run(["bash", str(ROOT / "packs/core" / tweak / script)],
                           env=sandbox_env(self.home, self.stubs, **env), capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout, r.stderr

    def install(self, tweak):
        d = self.home / ".local/share/frame-tweaks/vr-dashboard/patches"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "packs/core" / tweak / "patch.js", d / f"{tweak}.js")

    def conf(self, tweak):
        return self.home / ".config/frame-tweaks" / f"{tweak}.json"

    def test_flips_both_ways(self):
        for tweak in TWEAKS:
            with self.subTest(tweak):
                self.install(tweak)
                self.assertEqual(self.run_script(tweak, "run-label.sh")[1], "Turn off\n")    # (default: on)
                rc, out, err = self.run_script(tweak, "run.sh")
                self.assertEqual(rc, 0, err)
                self.assertTrue(out.startswith("Turned off"), out)
                self.assertEqual(json.loads(self.conf(tweak).read_text()), {"enabled": False})
                self.assertEqual(self.run_script(tweak, "run-label.sh")[1], "Turn on\n")
                rc, out, err = self.run_script(tweak, "status.sh")
                self.assertEqual(rc, 0, out + err)
                self.assertTrue(out.startswith("ok       installed, turned off"), out)

                rc, out, err = self.run_script(tweak, "run.sh")
                self.assertEqual(rc, 0, err)
                self.assertTrue(out.startswith("Turned on"), out)
                # (true, not removed: the watcher hands over only a file that exists, so the page
                # would keep the false it had)
                self.assertEqual(json.loads(self.conf(tweak).read_text()), {"enabled": True})
                self.assertEqual(self.run_script(tweak, "run-label.sh")[1], "Turn off\n")
                rc, out, _ = self.run_script(tweak, "status.sh")
                self.assertEqual((rc, out), (0, "ok       installed (active while SteamVR runs)\n"))
        said = self.log.read_text().splitlines()
        self.assertEqual(len(said), 6)
        self.assertTrue(said[0].startswith("Curved world windows|Turned off"), said[0])

    def test_other_settings_are_kept(self):
        self.install("curvature")
        self.conf("curvature").parent.mkdir(parents=True)
        self.conf("curvature").write_text('{"later": 1}\n')
        self.run_script("curvature", "run.sh")
        self.assertEqual(json.loads(self.conf("curvature").read_text()), {"later": 1, "enabled": False})

    def test_a_garbled_file_counts_as_on_and_is_replaced(self):
        self.install("float-grab")
        self.conf("float-grab").parent.mkdir(parents=True)
        self.conf("float-grab").write_text("{not json")
        self.assertEqual(self.run_script("float-grab", "run-label.sh")[1], "Turn off\n")
        self.run_script("float-grab", "run.sh")
        self.assertEqual(json.loads(self.conf("float-grab").read_text()), {"enabled": False})

    def test_not_installed(self):
        rc, out, _ = self.run_script("float-return", "run.sh")
        self.assertEqual(rc, 1)
        self.assertIn("Not installed: tick Back to the previous window", out)
        self.assertFalse(self.conf("float-return").exists())

    def test_uninstall_forgets_it_a_reinstall_keeps_it(self):
        for reinstall, kept in (("1", True), ("", False)):
            with self.subTest(reinstall=reinstall):
                self.install("curvature")
                if self.run_script("curvature", "run-label.sh")[1] == "Turn off\n":
                    self.run_script("curvature", "run.sh")
                self.assertEqual(self.run_script("curvature", "run-label.sh")[1], "Turn on\n")
                rc, _, err = self.run_script("curvature", "uninstall.sh", FRAME_TWEAKS_REINSTALL=reinstall)
                self.assertEqual(rc, 0, err)
                self.assertEqual(self.conf("curvature").exists(), kept)
                self.install("curvature")
                self.assertEqual(self.run_script("curvature", "run-label.sh")[1], "Turn on\n" if kept else "Turn off\n")


# ---- the patches, in Node ---------------------------------------------------------------------
# A fake page: timers run by hand (step), Date.now by hand, the config set between steps.
HARNESS = r"""
let now = 1000, timers = [], nextId = 1;
globalThis.setInterval = (fn, ms) => { const id = nextId++; timers.push({ id, fn }); return id; };
globalThis.clearInterval = (id) => { timers = timers.filter((t) => t.id !== id); };
Date.now = () => now;
globalThis.window = globalThis;
const step = (ms = 0) => { now += ms; for (const t of [...timers]) t.fn(); };
const setOn = (on) => {
  (window.__sftPatchConfig ??= {})[NAME] = on === null ? undefined : { enabled: on };
  window.__sftPatches?.[NAME]?.configChanged?.();
};
"""

CURVATURE = r"""
const NAME = 'curvature';
const frame = () => ({ docking: { dockLocation: 4 }, curvature: { m_bCurveOverride: undefined, shouldCurve: false,
                       ToggleCurvature() { this.m_bCurveOverride = !this.shouldCurve; this.shouldCurve = this.m_bCurveOverride; } } });
window.FrameStore = { frames: [] };
const out = [];
for (const on of [false, true, null]) {
  setOn(on);
  if (!window.__sftPatches?.[NAME]) eval(PATCH);
  const f = frame();
  window.FrameStore.frames.push(f);
  step(400); step(400);
  out.push(f.curvature.shouldCurve);
}
console.log(JSON.stringify(out));
"""

FLOAT_RETURN = r"""
const NAME = 'float-return';
const frames = {};
const add = (id, dock) => (frames[id] = { frameID: id, docking: { dockLocation: dock } });
let active = null, autoCalls = 0;
const switched = [];
window.FrameStore = { GetFrame: (id) => frames[id] };
window.DashboardStore = { get activeFrame() { return active; } };
window.Dashboard = { switchToFrameInternal: (f) => { switched.push(f.frameID); active = f; return true; },
                     autoSwitchOverlayIfNeeded() { autoCalls++; } };
const out = {};
for (const on of [false, true]) {
  setOn(on);
  if (!window.__sftPatches?.[NAME]) eval(PATCH);
  switched.length = 0;
  // A shown, then B; B floated out: 2.5 s later, back to A (when on).
  active = add('A' + on, 1); step(200);
  active = add('B' + on, 1); step(200);
  frames['B' + on].docking.dockLocation = 4; step(200);
  step(3000); step(200);
  // C shown, then closed: the dashboard's own choice (stock) or back to the one before (on).
  active = add('C' + on, 1); step(200);
  delete frames['C' + on]; active = null;
  const before = autoCalls;
  window.Dashboard.autoSwitchOverlayIfNeeded();
  step(400); step(400);
  out[on] = { switched: [...switched], stockAuto: autoCalls - before };
}
console.log(JSON.stringify(out));
"""

FLOAT_GRAB = r"""
const NAME = 'float-grab';
window.__sftLib = { DOCK: { Dashboard: 1, World: 4 }, walk: (visit) => fibers.find(visit) };
window.VRHTML = { VROverlay: { GetPrimaryDashboardDevice: () => 3 },
                  VRSystem: { GetControllerRoleForTrackedDeviceIndex: () => 2 } };   // (right hand; no trigger pose)
const fibers = [], frames = [];
let started = 0;
const add = () => {
  const f = { docking: { dockLocation: 1, beingDragged: false, SetDockLocation(loc) { this.dockLocation = loc; } } };
  frames.push(f);
  fibers.push({ stateNode: { props: { frame: f }, state: { xfTransform: {} },
                             startFloatingWindowMove() { started++; f.docking.beingDragged = true; },
                             endFloatingWindowMove() { f.docking.beingDragged = false; } } });
  return f;
};
window.FrameStore = { frames };
window.addEventListener = () => {}; window.removeEventListener = () => {};
const out = {};
for (const on of [false, true]) {
  setOn(on);
  if (!window.__sftPatches?.[NAME]) eval(PATCH);
  started = 0;
  const f = add();
  step(500);                                 // (wrapped by the patch's next look)
  f.docking.SetDockLocation(4);              // Float in World
  step(40);
  const held = f.docking.beingDragged;
  f.docking.SetDockLocation(1);              // Return to Dashboard, under the laser
  out[on] = { started, held, docked: f.docking.dockLocation === 1 };
}
// Turned off while one is held: it's put down.
setOn(true);
const g = add(); step(500); g.docking.SetDockLocation(4); step(40);
const heldBefore = g.docking.beingDragged;
setOn(false);
out.putDown = heldBefore && !g.docking.beingDragged;
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "needs Node.js to run the patches")
class PatchesHonourTheSwitch(unittest.TestCase):
    def run_patch(self, tweak, body):
        patch = (ROOT / "packs/core" / tweak / "patch.js").read_text()
        code = HARNESS + f"const PATCH = {json.dumps(patch)};\n" + body
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_curvature(self):
        # off: a new world window stays flat (stock); on, or no setting: curved
        self.assertEqual(self.run_patch("curvature", CURVATURE), [False, True, True])

    def test_float_return(self):
        out = self.run_patch("float-return", FLOAT_RETURN)
        self.assertEqual(out["false"], {"switched": [], "stockAuto": 1})
        self.assertEqual(out["true"], {"switched": ["Atrue", "Atrue"], "stockAuto": 0})

    def test_float_grab(self):
        out = self.run_patch("float-grab", FLOAT_GRAB)
        self.assertEqual(out["false"], {"started": 0, "held": False, "docked": True})
        self.assertEqual(out["true"], {"started": 1, "held": True, "docked": False})
        self.assertTrue(out["putDown"])


class WatcherForgetsARemovedPatchsSettings(unittest.TestCase):
    def test_stop_expr_drops_the_config(self):
        """Unticked (its uninstall removes "enabled": false) and ticked again: the page mustn't keep
        the old setting, which config_expr wouldn't replace (no file, nothing handed over)."""
        sft = load_script(ROOT / "packs/core/vr-dashboard/sft-dashboard", "sft_switch")
        self.assertIn('delete window.__sftPatchConfig?.["curvature"]', sft.stop_expr("curvature"))



CURVATURE_TURNED_ON_AGAIN = r"""
const NAME = 'curvature';
const frame = () => ({ docking: { dockLocation: 4 }, curvature: { m_bCurveOverride: undefined, shouldCurve: false,
                       ToggleCurvature() { this.m_bCurveOverride = !this.shouldCurve; this.shouldCurve = this.m_bCurveOverride; } } });
window.FrameStore = { frames: [] };
setOn(false);
eval(PATCH);
const a = frame(); window.FrameStore.frames.push(a); step(400);      // floated while off
setOn(true); step(400); step(400);
const b = frame(); window.FrameStore.frames.push(b); step(400);      // floated once it's on
a.docking.dockLocation = 1; step(400); a.docking.dockLocation = 4; step(400);   // docked, floated again
console.log(JSON.stringify({ keptFlat: !b.curvature.shouldCurve ? 'b flat?!' : true, aAfterTurnOn: null,
                             a: a.curvature.shouldCurve, b: b.curvature.shouldCurve }));
"""

FLOAT_RETURN_HISTORY_WHILE_OFF = r"""
const NAME = 'float-return';
const frames = {};
const add = (id, dock) => (frames[id] = { frameID: id, docking: { dockLocation: dock } });
let active = null;
const switched = [];
window.FrameStore = { GetFrame: (id) => frames[id] };
window.DashboardStore = { get activeFrame() { return active; } };
window.Dashboard = { switchToFrameInternal: (f) => { switched.push(f.frameID); active = f; return true; } };
setOn(true);
eval(PATCH);
active = add('P', 1); step(200);           // shown while on
setOn(false);
active = add('A', 1); step(200);           // shown while off
active = add('B', 1); step(200);
setOn(true); step(200);
frames.B.docking.dockLocation = 4; step(200);    // B floated out
step(3000); step(200);
console.log(JSON.stringify(switched));
"""


@unittest.skipUnless(shutil.which("node"), "needs Node.js to run the patches")
class TurnedOnAgain(PatchesHonourTheSwitch):
    """Found in a bug hunt: Turn on curved every world window floated while it was off, and Back to
    the previous window, after being off, went back to a window shown before it was turned off."""

    def test_curvature_leaves_windows_floated_while_off(self):
        out = self.run_patch("curvature", CURVATURE_TURNED_ON_AGAIN)
        self.assertEqual((out["a"], out["b"]), (True, True))   # (a: only once floated again with it on)

    def test_curvature_leaves_them_flat_right_after_turn_on(self):
        body = CURVATURE_TURNED_ON_AGAIN.replace("const b = frame();", "console.log(JSON.stringify({ a: a.curvature.shouldCurve })); process.exit(0); const b = frame();")
        self.assertEqual(self.run_patch("curvature", body), {"a": False})

    def test_float_return_goes_back_to_the_window_shown_before(self):
        self.assertEqual(self.run_patch("float-return", FLOAT_RETURN_HISTORY_WHILE_OFF), ["A"])


@unittest.skipUnless(shutil.which("node"), "needs Node.js to run the watcher's page code")
class SettingsFileGone(unittest.TestCase):
    """Found in a bug hunt: unticked (the uninstall deletes the settings file) and ticked again
    before the watcher's next pass, the page kept enabled: false: the patch stayed off while its
    status said on. A file that's gone now takes the page's copy with it."""

    def test_the_pages_copy_goes_with_the_file(self):
        sft = load_script(ROOT / "packs/core/vr-dashboard/sft-dashboard", "sft_switch2")
        with tempfile.TemporaryDirectory() as d:
            expr = sft.config_expr("curvature", Path(d) / "curvature.json")
        self.assertIsNotNone(expr)
        code = ("globalThis.window = globalThis; let told = 0;"
                "window.__sftPatchConfig = { curvature: { enabled: false }, other: { x: 1 } };"
                "window.__sftPatches = { curvature: { configChanged: () => told++ } };"
                f"eval({json.dumps(expr)});"
                "console.log(JSON.stringify({ conf: window.__sftPatchConfig, told }));")
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(json.loads(r.stdout), {"conf": {"other": {"x": 1}}, "told": 1}, r.stderr)

    def test_a_garbled_file_leaves_the_page_alone(self):
        sft = load_script(ROOT / "packs/core/vr-dashboard/sft-dashboard", "sft_switch3")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "curvature.json").write_text("{nope")
            self.assertIsNone(sft.config_expr("curvature", Path(d) / "curvature.json"))

if __name__ == "__main__":
    unittest.main()
