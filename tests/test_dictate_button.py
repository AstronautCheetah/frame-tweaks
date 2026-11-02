"""Dictation's controller button (packs/core/dictation/dictate-button, lib/vrkit.py ButtonReader):
a hold of DICTATE_BUTTON_HOLD seconds toggles once, the moment it's reached, and a shorter press
never does; the settings come from dictate.conf (Menu and 0.6 s unless it says otherwise; off
turns it off; anything it can't read keeps the default); the reader takes the press from the
controller model part's IsPressed flag, and says None without that controller or part. Install
sets up the service with SteamVR (PartOf/WantedBy steamvr.service) and leaves it out without
SteamVR's library, before downloading anything; uninstall removes it. A stand-in openvr module
and stand-in commands stand in for SteamVR, systemd and Homebrew."""
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DICTATION = ROOT / "packs/core/dictation"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script, sandbox_env, stub  # noqa: E402
import vrkit  # noqa: E402  (lib/, put on sys.path by helpers)

db = load_script(DICTATION / "dictate-button")


class Settings(unittest.TestCase):
    def test_defaults_and_what_dictate_conf_says(self):
        self.assertEqual(db.settings(""), ("menu", 0.6))
        self.assertEqual(db.settings((DICTATION / "dictate.conf.example").read_text()), ("menu", 0.6))
        self.assertEqual(db.settings("DICTATE_BUTTON=y\nDICTATE_BUTTON_HOLD=1.2\n"), ("y", 1.2))
        self.assertEqual(db.settings('DICTATE_BUTTON="off"'), (None, 0.6))
        self.assertEqual(db.settings("export DICTATE_BUTTON='Y'  # the other one\n"), ("y", 0.6))
        self.assertEqual(db.settings("DICTATE_BUTTON=y\nDICTATE_BUTTON=menu\n"), ("menu", 0.6))   # (the last wins)

    def test_what_it_cant_read_keeps_the_default(self):
        self.assertEqual(db.settings("DICTATE_BUTTON=trigger\nDICTATE_BUTTON_HOLD=long\n"), ("menu", 0.6))
        self.assertEqual(db.settings("#DICTATE_BUTTON=off\n"), ("menu", 0.6))
        self.assertEqual(db.settings("DICTATE_BUTTON_HOLD=0.01"), ("menu", 0.2))
        self.assertEqual(db.settings("DICTATE_BUTTON_HOLD=60"), ("menu", 3.0))


class HoldToToggle(unittest.TestCase):
    def feed(self, samples, seconds=0.6):
        """samples: (time, down); the times it fired."""
        h = db.Hold(seconds)
        return [t for t, down in samples if h.feed(t, down)]

    def test_fires_once_per_hold_when_it_has_been_held_long_enough(self):
        held = [(t / 10, True) for t in range(0, 30)]          # held 3 s
        self.assertEqual(self.feed(held), [0.6])

    def test_short_presses_never_fire(self):
        taps = [(0.0, True), (0.3, True), (0.4, False), (0.5, True), (0.9, True), (1.0, False)]
        self.assertEqual(self.feed(taps), [])

    def test_each_new_hold_fires_again_and_a_lost_controller_resets(self):
        s = [(0.0, True), (0.7, True), (0.8, False), (1.0, True), (1.7, True),
             (1.8, None), (2.0, True), (2.5, True), (2.6, True)]
        self.assertEqual(self.feed(s), [0.7, 1.7, 2.6])


class FakeVR(types.SimpleNamespace):
    """Just enough of the openvr module for ButtonReader."""

    def __init__(self):
        super().__init__(TrackedControllerRole_LeftHand=1, TrackedControllerRole_RightHand=2,
                         k_unTrackedDeviceIndexInvalid=0xFFFFFFFF, Prop_RenderModelName_String=1003,
                         VRComponentProperty_IsPressed=1 << 3, RenderModel_ControllerMode_State_t=object)
        self.device, self.parts, self.flags = 4, {"button_menu", "button_y"}, 0
        vr = self

        class System:
            def getTrackedDeviceIndexForControllerRole(self, role):
                return vr.device if role == 2 else vr.k_unTrackedDeviceIndexInvalid

            def isTrackedDeviceConnected(self, d):
                return True

            def getStringTrackedDeviceProperty(self, d, prop):
                return "{frame_controller}frame_controller_right"

        class Models:
            def getComponentStateForDevicePath(self, model, part, path, mode):
                return (part in vr.parts), types.SimpleNamespace(uProperties=vr.flags)

        class Input:
            def getInputSourceHandle(self, path):
                return 77

        self.VRSystem, self.VRRenderModels, self.VRInput = System, Models, Input


class Reader(unittest.TestCase):
    def test_reads_the_model_parts_pressed_flag(self):
        vr = FakeVR()
        r = vrkit.ButtonReader(vr, "right", "button_menu")
        self.assertIs(r.pressed(), False)
        vr.flags = vr.VRComponentProperty_IsPressed | 1          # (pressed, and visible)
        self.assertIs(r.pressed(), True)
        self.assertEqual(r.device, 4)

    def test_none_without_that_controller_or_part(self):
        vr = FakeVR()
        self.assertIsNone(vrkit.ButtonReader(vr, "left", "button_menu").pressed())
        self.assertIsNone(vrkit.ButtonReader(vr, "right", "button_view").pressed())
        r = vrkit.ButtonReader(vr, "right", "button_y")
        vr.device = vr.k_unTrackedDeviceIndexInvalid
        self.assertIsNone(r.pressed())
        self.assertIsNone(r.device)


class InstallService(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "home"
        models = self.home / ".local/share/whisper"
        models.mkdir(parents=True)
        (models / "ggml-small-q8_0.bin").write_text("")
        self.log = self.tmp / "log"
        self.log.write_text("")
        self.stubs, ydotool = self.tmp / "stubs", self.tmp / "ydotool"
        for name in ("brew", "systemctl", "pip"):
            stub(self.stubs, name, f'echo "{name} $*" >> {self.log}')
        stub(ydotool, "install.sh", "true")
        self.unit = self.home / ".config/systemd/user/frame-tweaks-dictate-button.service"
        self.env = sandbox_env(self.home, self.stubs, BREW_BIN=self.stubs / "brew",
                               FRAME_TWEAKS_DIRS=f"ydotool={ydotool}", FRAME_TWEAKS_VR_LIB=self.tmp / "no-steamvr.so")

    def run_script(self, name):
        r = subprocess.run(["bash", str(DICTATION / name)], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def with_steamvr(self):
        """SteamVR's library, and a tools venv whose Python already has jeepney and openvr."""
        lib = self.tmp / "libopenvr_api.so"
        lib.write_text("")
        ovr = self.tmp / "site/openvr"
        ovr.mkdir(parents=True)
        stub(self.home / ".local/share/frame-tweaks/venv/bin", "python",
             f'case "$*" in *print*) echo "{ovr}" ;; esac; exit 0')
        self.env["FRAME_TWEAKS_VR_LIB"] = str(lib)
        return ovr

    def test_without_steamvr_no_service_and_nothing_downloaded(self):
        r = self.run_script("install.sh")
        self.assertFalse(self.unit.exists())
        self.assertFalse((self.home / ".local/bin/dictate-button").exists())
        self.assertFalse((self.home / ".local/share/frame-tweaks/venv").exists())   # (no venv made for it)
        self.assertIn("No SteamVR here", r.stderr)

    def test_with_steamvr_the_service_follows_steamvr_and_uninstall_removes_it(self):
        ovr = self.with_steamvr()
        self.run_script("install.sh")
        unit = self.unit.read_text()
        for line in ("PartOf=steamvr.service", "After=steamvr.service", "WantedBy=steamvr.service",
                     f"ExecStart={self.home}/.local/bin/dictate-button"):
            self.assertIn(line, unit)
        tool = (self.home / ".local/bin/dictate-button").read_text()
        self.assertTrue(tool.startswith(f"#!{self.home}/.local/share/frame-tweaks/venv/bin/python\n"))
        self.assertTrue((ovr / "libopenvr_api_64.so").is_symlink())
        self.assertIn("systemctl --user enable frame-tweaks-dictate-button.service", self.log.read_text())
        self.run_script("uninstall.sh")
        self.assertFalse(self.unit.exists())
        self.assertFalse((self.home / ".local/bin/dictate-button").exists())
        self.assertIn("systemctl --user disable --now frame-tweaks-dictate-button.service", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
