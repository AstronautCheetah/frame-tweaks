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


class EveryButton(unittest.TestCase):
    """Every DICTATE_BUTTON value the settings page offers is one dictate-button reads, and the
    other way round; the system buttons aren't among them (SteamVR keeps them)."""

    def test_settings_page_and_buttons_agree(self):
        import manifest
        meta, _ = manifest.front_matter((DICTATION / "README.md").read_text())
        opt = next(o for o in meta["settings"]["options"] if o["key"] == "DICTATE_BUTTON")
        offered = {c["value"] for c in opt["choices"]}
        self.assertEqual(offered, set(db.BUTTONS) | {"off"})
        for value in offered:
            self.assertEqual(db.settings(f"DICTATE_BUTTON={value}")[0], None if value == "off" else value)
        self.assertFalse([b for b in db.BUTTONS if "system" in db.BUTTONS[b][1]])
        tiers = [c["label"].split(":")[0] for c in opt["choices"]]
        self.assertEqual(tiers, sorted(tiers, key=["Recommended", "Alternative", "Not recommended"].index))


class Aux(unittest.TestCase):
    """The headset's Aux button, read from its input device without taking it: KEY_SELECT down
    and up, other keys and auto-repeat ignored; None without the device."""

    def events(self, *evs):
        f = tempfile.NamedTemporaryFile(delete=False)
        self.addCleanup(Path(f.name).unlink)
        for kind, code, value in evs:
            f.write(db.EVENT.pack(0, 0, kind, code, value))
        f.close()
        return f.name

    def test_key_select_down_and_up(self):
        r = db.AuxReader(self.events((1, 353, 1), (0, 0, 0), (1, 115, 1)))     # (Aux down, a sync, volume up)
        self.assertIs(r.pressed(), True)
        self.assertIs(r.pressed(), True)                                       # (still held: nothing new)
        r2 = db.AuxReader(self.events((1, 353, 1), (1, 353, 2), (1, 353, 0)))  # (down, repeat, up)
        self.assertIs(r2.pressed(), False)
        self.assertIsNone(r2.device)                                           # (no controller to tick)

    def test_none_without_the_device(self):
        self.assertIsNone(db.AuxReader("/nonexistent/event99").pressed())


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


class MenuEntry(unittest.TestCase):
    """DICTATE_MENU: Dictate (toggle) hidden in the menus (NoDisplay) while a controller button
    is set (auto, the default), or always shown or hidden; the entry and Frame Tweaks' record of
    it change alike, only NoDisplay in [Desktop Entry]; the option sits above the button's."""

    ENTRY = "[Desktop Entry]\nType=Application\nName=Dictate (toggle)\nNoDisplay=false\n\n[Desktop Action x]\nNoDisplay=keep\n"

    def run_menu(self, conf, button_tool=True):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            entries = [home / ".local/share/applications/dictate.desktop",
                       home / ".local/share/frame-tweaks/menu-built/dictate.desktop"]
            for e in entries:
                e.parent.mkdir(parents=True)
                e.write_text(self.ENTRY)
            (home / ".config/frame-tweaks").mkdir(parents=True)
            (home / ".config/frame-tweaks/dictate.conf").write_text(conf)
            if button_tool:
                stub(home / ".local/bin", "dictate-button", "true")
            env = sandbox_env(home)
            for _ in range(2):                                   # (a second run changes nothing)
                r = subprocess.run(["bash", str(DICTATION / "dictate-menu")], env=env, capture_output=True,
                                   text=True, timeout=30)
                self.assertEqual(r.returncode, 0, r.stderr)
            texts = [e.read_text() for e in entries]
            self.assertEqual(texts[0], texts[1])
            self.assertIn("NoDisplay=keep", texts[0])             # (another group's line kept)
            main = texts[0].split("\n\n")[0]
            self.assertLessEqual(main.count("NoDisplay="), 1)
            return "NoDisplay=true" in main

    def test_auto_hides_while_a_button_is_set(self):
        self.assertTrue(self.run_menu(""))                                     # (the defaults: Menu, auto)
        self.assertFalse(self.run_menu("DICTATE_BUTTON=off\n"))
        self.assertFalse(self.run_menu("", button_tool=False))                 # (no SteamVR, no button)

    def test_always_or_never(self):
        self.assertFalse(self.run_menu("DICTATE_MENU=yes\n"))
        self.assertTrue(self.run_menu("DICTATE_MENU='no'\nDICTATE_BUTTON=off\n"))

    def test_the_menu_option_comes_before_the_buttons(self):
        import manifest
        meta, _ = manifest.front_matter((DICTATION / "README.md").read_text())
        keys = [o["key"] for o in meta["settings"]["options"]]
        self.assertLess(keys.index("DICTATE_MENU"), keys.index("DICTATE_BUTTON"))


class StatusLine(unittest.TestCase):
    """Dictation's status line (the window's tip for it) names the button that's chosen, says so
    when it's off, takes a value it doesn't know as Menu (as dictate-button does), and says
    nothing of a button without SteamVR (no dictate-button)."""

    def status(self, conf, button_tool=True):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            stub(home / ".local/bin", "dictate", "true")
            if button_tool:
                stub(home / ".local/bin", "dictate-button", "true")
            (home / ".local/share/whisper").mkdir(parents=True)
            (home / ".local/share/whisper/ggml-small-q8_0.bin").write_text("")
            (home / ".config/frame-tweaks").mkdir(parents=True)
            (home / ".config/frame-tweaks/dictate.conf").write_text(conf)
            stubs = home / "stubs"
            stub(stubs, "whisper-cli", "true")
            stub(stubs, "systemctl", "exit 3")                       # (SteamVR not running)
            r = subprocess.run(["bash", str(DICTATION / "status.sh")], env=sandbox_env(home, stubs),
                               capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout.strip()

    def test_names_the_chosen_button(self):
        self.assertIn("hold Menu on the right controller to dictate", self.status(""))
        self.assertIn("hold Y on the right controller to dictate", self.status("DICTATE_BUTTON=y\n"))
        self.assertIn("hold d-pad up on the left controller to dictate", self.status("DICTATE_BUTTON=dpad_up\n"))
        self.assertIn("hold Aux on the headset to dictate", self.status('DICTATE_BUTTON="aux"\n'))
        self.assertIn("hold the left grip to dictate", self.status("DICTATE_BUTTON=grip_left\n"))
        self.assertIn("hold Menu on the right controller", self.status("DICTATE_BUTTON=trigger\n"))   # (unknown: Menu)

    def test_off_and_without_steamvr(self):
        self.assertIn("no controller button", self.status("DICTATE_BUTTON=off\n"))
        plain = self.status("DICTATE_BUTTON=y\n", button_tool=False)
        self.assertNotIn("hold", plain)
        self.assertNotIn("controller", plain)

    def test_every_button_has_a_name(self):
        names = (DICTATION / "button-names.sh").read_text()
        for value in db.BUTTONS:
            self.assertIn(f"\n        {value}) t '", names, value)


class DpadDirection(unittest.TestCase):
    """The d-pad is one part of the model, tilted about one axis per direction (measured on a
    Frame): each axis is its direction, a diagonal (10°, between two) is none, and so is a part
    barely tilted."""

    @staticmethod
    def turned(axis, degrees):
        """A rest pose (identity) and the pose turned by degrees about axis, as m rows."""
        x, y, z = axis
        n = (x * x + y * y + z * z) ** 0.5
        x, y, z = x / n, y / n, z / n
        import math
        c, s, t = math.cos(math.radians(degrees)), math.sin(math.radians(degrees)), 1 - math.cos(math.radians(degrees))
        rot = [[t * x * x + c, t * x * y - s * z, t * x * z + s * y, 0],
               [t * x * y + s * z, t * y * y + c, t * y * z - s * x, 0],
               [t * x * z - s * y, t * y * z + s * x, t * z * z + c, 0]]
        ident = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]
        return types.SimpleNamespace(m=ident), types.SimpleNamespace(m=rot)

    def test_each_direction_and_not_diagonals(self):
        for name, axis in vrkit.DPAD_AXES.items():
            self.assertEqual(vrkit.dpad_direction(*vrkit.rotation_axis(*self.turned(axis, 7))), name)
        up, left = vrkit.DPAD_AXES["dpad_up"], vrkit.DPAD_AXES["dpad_left"]
        diagonal = tuple(a + b for a, b in zip(up, left))
        self.assertIsNone(vrkit.dpad_direction(*vrkit.rotation_axis(*self.turned(diagonal, 10))))
        self.assertIsNone(vrkit.dpad_direction(*vrkit.rotation_axis(*self.turned(up, 1))))


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


    def test_a_reinstall_keeps_the_downloads_an_uninstall_removes_them(self):
        """↻ (FRAME_TWEAKS_REINSTALL) removed Parakeet's model and runtime and the Whisper models
        too, all downloaded again (about 1.1 GB): they stay; an uninstall still removes them."""
        share = self.home / ".local/share"
        files = [share / "frame-tweaks/parakeet/model/encoder.onnx", share / "whisper/ggml-silero-v6.2.0.bin",
                 share / "whisper/ggml-small-q8_0.bin"]
        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x")
        self.env["FRAME_TWEAKS_REINSTALL"] = "1"
        self.run_script("uninstall.sh")
        self.assertTrue(all(f.exists() for f in files))
        del self.env["FRAME_TWEAKS_REINSTALL"]
        self.run_script("uninstall.sh")
        self.assertFalse(any(f.exists() for f in files))


class SettingsPage(unittest.TestCase):
    """What Dictation's ⚙ Settings writes (./install.sh settings, the window's page) is what
    dictate-button reads, and the example settings stay commented out around it."""

    def test_the_settings_page_writes_what_dictate_button_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            conf = home / ".config/frame-tweaks/dictate.conf"
            conf.parent.mkdir(parents=True)
            conf.write_text((DICTATION / "dictate.conf.example").read_text())
            env = sandbox_env(home, path=("/usr/bin", "/bin", str(Path(sys.executable).parent)))
            for args, want in ((["DICTATE_BUTTON=y", "DICTATE_BUTTON_HOLD=1"], ("y", 1.0)),
                               (["DICTATE_BUTTON=off"], (None, 1.0)),
                               (["--reset"], ("menu", 0.6))):
                r = subprocess.run(["bash", str(ROOT / "install.sh"), "settings", "dictation", *args],
                                   env=env, capture_output=True, text=True, timeout=60, cwd=ROOT)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(db.settings(conf.read_text()), want, args)
            self.assertIn("#DICTATE_PROMPT=", conf.read_text())                 # (kept)


if __name__ == "__main__":
    unittest.main()
