"""VR memory guard (packs/core/vr-memory-guard): install gives Flatpak apps (app.slice) a limit of
the device's memory minus the reserve for VR, every Firefox scope its own, and SteamVR the lowest
OOM score a user service may have; it sets the running slice and Firefox at once; it refuses a
reserve that leaves too little and a size it can't read; uninstall lifts the limits and keeps the
settings; the status line reads the slice's limit and use. A fake /proc/meminfo and cgroup folder
stand in for the Frame's.

vr-memory-guard-tool, which install runs for the Flatpak apps: each app's own limit or "shared" in
vr-memory-guard-apps.conf, the reserve for VR, Firefox's old firefox_max moved there; it refuses
what it can't use with a message, never a traceback; and its file reader never crashes on any
text."""
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TWEAK = ROOT / "packs/core/vr-memory-guard"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script, sandbox_env, stub  # noqa: E402

DROPIN = "frame-tweaks-vr-memory-guard.conf"
TOOL = TWEAK / "vr-memory-guard-tool"
FIREFOX = "app-flatpak-org.mozilla.firefox-.scope"


class Base(unittest.TestCase):
    """A throwaway home with stand-ins for systemctl, flatpak, /proc/meminfo and the cgroups."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.meminfo = self.home / "meminfo"
        self.meminfo.write_text("MemTotal:       16037888 kB\nMemFree:  1000 kB\n")   # (15662 MiB, the Frame's)
        self.calls = self.home / "systemctl.log"
        self.stubs = self.home / "stubs"
        # flatpak: three apps installed. systemctl: logs its arguments; one running Firefox scope;
        # SteamVR running.
        stub(self.stubs, "flatpak", 'printf "org.mozilla.firefox\\norg.signal.Signal\\norg.kde.kdenlive\\n"')
        stub(self.stubs, "systemctl", f'echo "$*" >> "{self.calls}"\n'
             'case "$*" in *list-units*) echo "app-flatpak-org.mozilla.firefox-4242.scope loaded active running x" ;; '
             '*is-active*) exit 0 ;; esac')
        self.cg = self.home / "cgroup"
        (self.cg / "app.slice").mkdir(parents=True)
        (self.cg / "cgroup.controllers").write_text("cpu memory pids\n")
        self.env = sandbox_env(self.home, self.stubs, FRAME_TWEAKS_MEMINFO=self.meminfo,
                               FRAME_TWEAKS_CGROUP_USER=self.cg)
        self.conf = self.home / ".config/frame-tweaks/vr-memory-guard.conf"
        self.units = self.home / ".config/systemd/user"
        self.apps_file = self.home / ".config/frame-tweaks/vr-memory-guard-apps.conf"

    def run_script(self, name, ok=True):
        r = subprocess.run(["bash", str(TWEAK / name)], env=self.env, capture_output=True, text=True, timeout=30)
        if ok is not None:
            self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def dropin(self, unit):
        return (self.units / f"{unit}.d" / DROPIN).read_text()

    def tool(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(TOOL), *args], env=self.env, capture_output=True, text=True, timeout=30)
        if ok is not None:
            self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        return r


class VrMemoryGuard(Base):
    def test_limits_follow_the_memory_and_the_settings(self):
        self.run_script("install.sh")
        self.assertIn("MemoryMax=10542M", self.dropin("app.slice"))           # 15662 - 5120
        self.assertIn("MemorySwapMax=2048M", self.dropin("app.slice"))
        self.assertIn("MemoryMax=5120M", self.dropin("app-flatpak-org.mozilla.firefox-.scope"))
        self.assertIn("OOMScoreAdjust=100", self.dropin("steamvr.service"))
        self.assertNotIn("MemoryHigh", self.dropin("app.slice") + self.dropin("app-flatpak-org.mozilla.firefox-.scope"))
        self.conf.write_text("reserve_for_vr=6G\napps_swap_max=0\nfirefox_max=3500M\nfirefox_swap_max=512M\n")
        self.run_script("install.sh")
        self.assertIn("MemoryMax=9518M", self.dropin("app.slice"))
        self.assertIn("MemorySwapMax=0M", self.dropin("app.slice"))
        self.assertIn("MemoryMax=3500M", self.dropin("app-flatpak-org.mozilla.firefox-.scope"))

    def test_frame_tweaks_own_helpers_get_limits_of_their_own(self):
        """Dictation's services and Android Mirror's slice (scrcpy ran in steam.service from Steam's
        + menu, unlimited); a limits file from before these settings gets the defaults."""
        self.run_script("install.sh")
        for unit in ("frame-tweaks-dictate-engine.service", "frame-tweaks-dictate-button.service"):
            self.assertIn("MemoryMax=2500M", self.dropin(unit))
        self.assertIn("MemoryMax=1024M", self.dropin("app-ftmirror.slice"))
        self.conf.write_text("reserve_for_vr=5G\napps_swap_max=2G\nfirefox_max=5G\nfirefox_swap_max=1G\n"
                             "dictation_max=3G\nmirror_max=768M\n")
        self.run_script("install.sh")
        self.assertIn("MemoryMax=3072M", self.dropin("frame-tweaks-dictate-engine.service"))
        self.assertIn("MemoryMax=768M", self.dropin("app-ftmirror.slice"))
        self.run_script("uninstall.sh")
        self.assertFalse((self.units / "app-ftmirror.slice.d").exists())

    def test_running_slice_and_firefox_are_set_at_once(self):
        self.run_script("install.sh")
        log = self.calls.read_text()
        self.assertIn("--user set-property --runtime app.slice MemoryMax=10542M MemorySwapMax=2048M", log)
        self.assertIn("--user set-property --runtime app-flatpak-org.mozilla.firefox-4242.scope MemoryMax=5120M", log)

    def test_refuses_a_reserve_that_leaves_too_little_or_a_size_it_cant_read(self):
        self.conf.parent.mkdir(parents=True)
        for bad, says in (("reserve_for_vr=14G", "less than 2 GB"), ("reserve_for_vr=5 GB", "should be a size"),
                          ("reserve_for_vr=-1G", "should be a size"), ("reserve_for_vr=", "should be a size")):
            self.conf.write_text(f"{bad}\napps_swap_max=2G\nfirefox_max=5G\nfirefox_swap_max=1G\n")
            r = self.run_script("install.sh", ok=False)
            self.assertIn(says, r.stderr, bad)
            self.assertFalse((self.units / "app.slice.d" / DROPIN).exists(), bad)

    def test_uninstall_lifts_the_limits_and_keeps_the_settings(self):
        self.run_script("install.sh")
        self.run_script("uninstall.sh")
        for unit in ("app.slice", "app-flatpak-org.mozilla.firefox-.scope", "steamvr.service"):
            self.assertFalse((self.units / f"{unit}.d").exists(), unit)
        self.assertIn("set-property --runtime app.slice MemoryMax=infinity MemorySwapMax=infinity", self.calls.read_text())
        self.assertTrue(self.conf.exists())

    def test_uninstall_removes_every_apps_own_limit_and_the_tool(self):
        self.run_script("install.sh")
        self.tool("set", "org.signal.Signal", "2G")
        self.tool("apply")
        self.assertTrue((self.home / ".local/bin/vr-memory-guard-tool").exists())
        self.calls.write_text("")
        self.run_script("uninstall.sh")
        self.assertFalse((self.units / "app-flatpak-org.signal.Signal-.scope.d").exists())
        self.assertFalse((self.units / f"{FIREFOX}.d").exists())
        self.assertFalse((self.home / ".local/bin/vr-memory-guard-tool").exists())
        self.assertIn("set-property --runtime app-flatpak-org.mozilla.firefox-4242.scope MemoryMax=infinity",
                      self.calls.read_text())
        self.assertIn("org.signal.Signal 2G", self.apps_file.read_text())          # (kept, as the limits are)

    def test_status(self):
        r = self.run_script("status.sh", ok=False)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.run_script("install.sh")
        (self.cg / "app.slice/memory.max").write_text("max\n")              # (not applied yet)
        r = self.run_script("status.sh", ok=None)
        self.assertEqual(r.returncode, 2, r.stdout)
        (self.cg / "app.slice/memory.max").write_text(f"{10542 * 1048576}\n")
        (self.cg / "app.slice/memory.current").write_text(f"{1900 * 1048576}\n")
        r = self.run_script("status.sh")
        self.assertIn("Flatpak apps 1900 of 10542 MB (apps with a limit of their own: 1)", r.stdout)
        (self.cg / "cgroup.controllers").write_text("cpu pids\n")
        self.assertEqual(self.run_script("status.sh", ok=None).returncode, 2)


class Tool(Base):
    """vr-memory-guard-tool after an install (setUp's Frame: 15662 MB, 5G kept for VR: a 10542 MB
    pool; Firefox, Signal and Kdenlive installed; a Firefox open)."""
    def setUp(self):
        super().setUp()
        self.run_script("install.sh")
        self.calls.write_text("")

    def test_a_fresh_install_gives_firefox_its_old_default(self):
        text = self.apps_file.read_text()
        self.assertIn("org.mozilla.firefox 5G 1G\n", text)
        self.assertTrue(text.startswith("# VR memory guard"))
        self.assertNotIn("firefox_max=", self.conf.read_text())         # (the shipped settings no longer have it)

    def test_list_and_info(self):
        self.tool("set", "org.kde.kdenlive", "shared")
        self.tool("set", "org.gone.App", "3G")                           # (not installed: kept, listed only by info)
        rows = [line.split("\t") for line in self.tool("list").stdout.splitlines()]
        self.assertEqual(rows, [["org.kde.kdenlive", "shared", "-"], ["org.mozilla.firefox", "5G", "1G"],
                                ["org.signal.Signal", "shared", "-"]])
        info = json.loads(self.tool("info").stdout)
        self.assertEqual((info["total"], info["reserve"], info["pool"], info["max_reserve"]), (15662, 5120, 10542, 13614))
        apps = {a["id"]: a for a in info["apps"]}
        self.assertEqual(apps["org.mozilla.firefox"], {"id": "org.mozilla.firefox", "limit": 5120, "swap": 1024,
                                                       "installed": True})
        self.assertEqual(apps["org.gone.App"]["installed"], False)
        self.assertIsNone(apps["org.signal.Signal"]["limit"])

    def test_a_limit_writes_its_drop_in_and_sets_the_open_app(self):
        r = self.tool("set", "org.signal.Signal", "2560M")
        self.assertIn("apply", r.stdout)
        self.assertFalse((self.units / "app-flatpak-org.signal.Signal-.scope.d").exists())   # (set only saves)
        self.tool("set", "org.mozilla.firefox", "3G", "512M")
        self.tool("apply")
        self.assertEqual(self.dropin("app-flatpak-org.signal.Signal-.scope"),
                         "[Scope]\nMemoryMax=2560M\nMemorySwapMax=1024M\n")
        self.assertIn("MemoryMax=3072M\nMemorySwapMax=512M", self.dropin(FIREFOX))
        log = self.calls.read_text()
        self.assertIn("daemon-reload", log)
        self.assertIn("set-property --runtime app-flatpak-org.mozilla.firefox-4242.scope MemoryMax=3072M MemorySwapMax=512M", log)
        self.assertIn("set-property --runtime app.slice MemoryMax=10542M", log)

    def test_shared_removes_the_drop_in_and_lifts_the_open_apps_limit(self):
        self.tool("set", "org.mozilla.firefox", "shared")
        self.tool("apply")
        self.assertFalse((self.units / f"{FIREFOX}.d").exists())
        self.assertIn("org.mozilla.firefox shared", self.apps_file.read_text())
        self.assertIn("set-property --runtime app-flatpak-org.mozilla.firefox-4242.scope MemoryMax=infinity",
                      self.calls.read_text())
        self.run_script("install.sh")                                    # (a reinstall keeps it shared)
        self.assertFalse((self.units / f"{FIREFOX}.d").exists())
        # (a line deleted by hand: shared too, its drop-in goes at the next apply)
        self.tool("set", "org.signal.Signal", "1G")
        self.tool("apply")
        self.apps_file.write_text("org.mozilla.firefox shared\n")
        self.tool("apply")
        self.assertFalse((self.units / "app-flatpak-org.signal.Signal-.scope.d").exists())

    def test_what_cant_be_used_is_refused_with_a_message(self):
        before = self.apps_file.read_text()
        for args, says in ((["set", "../evil", "1G"], "isn't a Flatpak app ID"),
                           (["set", "firefox", "1G"], "isn't a Flatpak app ID"),
                           (["set", "org.foo-x.bar", "1G"], "isn't a Flatpak app ID"),
                           (["set", "org.example.App", "5 GB"], "isn't a limit"),
                           (["set", "org.example.App", "5.5G"], "isn't a limit"),
                           (["set", "org.example.App", "100M"], "256M at least"),
                           (["set", "org.example.App", "-1G"], "isn't a limit"),
                           (["set", "org.example.App", "11G"], "more than all Flatpak apps together"),
                           (["set", "org.example.App", "2G", "lots"], "isn't a swap size"),
                           (["set", "org.example.App", "shared", "1G"], "takes no swap"),
                           (["reserve", "14G"], "less than 2 GB"),
                           (["reserve", "512M"], "1G at least"),
                           (["reserve", "abc"], "isn't a size"),
                           (["frobnicate"], "vr-memory-guard-tool list")):
            r = self.tool(*args, ok=False)
            self.assertIn(says, r.stderr, args)
        self.assertEqual(self.apps_file.read_text(), before)
        self.assertIn("reserve_for_vr=5G", self.conf.read_text())
        self.tool("set", "org.foo", "1G")                                # (two parts are enough for Flatpak)

    def test_a_file_it_cant_read_stops_apply_and_names_the_line(self):
        self.apps_file.write_text("org.mozilla.firefox 5G\n\nnot an id\norg.mozilla.firefox shared\n")
        r = self.tool("apply", ok=False)
        self.assertIn("line 3", r.stderr)
        self.assertIn("line 4: org.mozilla.firefox is already on an earlier line", r.stderr)
        self.assertIn("MemoryMax=5120M", self.dropin(FIREFOX))           # (nothing changed)
        self.assertNotEqual(self.run_script("install.sh", ok=False).returncode, 0)

    def test_firefox_max_from_before_is_moved_into_the_apps_file(self):
        """A limits file from before each app had its own: Firefox keeps its limit, the old keys are
        commented out (read once), and the next install doesn't put the default back."""
        self.apps_file.unlink()
        self.conf.write_text("reserve_for_vr=5G\napps_swap_max=2G\nfirefox_max=3500M\nfirefox_swap_max=512M\n")
        self.assertIn("org.mozilla.firefox\t3500M\t512M", self.tool("list").stdout)   # (read only: nothing moved yet)
        self.assertFalse(self.apps_file.exists())
        self.run_script("install.sh")
        self.assertIn("org.mozilla.firefox 3500M 512M", self.apps_file.read_text())
        self.assertIn("MemoryMax=3500M\nMemorySwapMax=512M", self.dropin(FIREFOX))
        conf = self.conf.read_text()
        self.assertIn("# firefox_max=3500M", conf)
        self.assertNotIn("\nfirefox_max=", conf)
        self.run_script("install.sh")
        self.assertIn("MemoryMax=3500M", self.dropin(FIREFOX))
        # firefox_max written again (a backup restored): it's newer than Firefox's line, so it wins
        with self.conf.open("a") as f:
            f.write("firefox_max=4G\n")
        self.tool("apply")
        self.assertIn("org.mozilla.firefox 4G 512M", self.apps_file.read_text())
        self.assertIn("MemoryMax=4096M", self.dropin(FIREFOX))
        self.conf.write_text(self.conf.read_text() + "firefox_max=5 GB\n")
        self.assertIn("firefox_max", self.tool("apply", ok=False).stderr)

    def test_reserve_for_vr_bounds(self):
        r = self.tool("reserve", "6G")
        self.assertIn("9518 MB", r.stdout)
        self.assertIn("reserve_for_vr=6G\n", self.conf.read_text())
        self.assertIn("dictation_max=2500M", self.conf.read_text())                 # (other lines kept)
        self.tool("apply")
        self.assertIn("MemoryMax=9518M", self.dropin("app.slice"))
        self.tool("reserve", "13614M")                                   # (exactly 2 GB left for the apps)
        self.assertIn("less than 2 GB", self.tool("reserve", "13615M", ok=False).stderr)
        self.assertIn("(2048 MB)", self.tool("set", "org.example.App", "3G", ok=False).stderr)
        # an app's limit above a pool made smaller since: a warning, and the pool applies first
        r = self.tool("apply")
        self.assertIn("org.mozilla.firefox: its limit (5G) is more than", r.stderr)
        self.assertIn("MemoryMax=5120M", self.dropin(FIREFOX))


class AppsFile(unittest.TestCase):
    """The apps file's reader and writer, in-process."""
    tool = load_script(TOOL, "vr_memory_guard_tool")

    def test_round_trip(self):
        apps = {"org.mozilla.firefox": (5120, 1024), "org.signal.Signal": None, "com.example.My_App-2": (2560, 0),
                "org.kde.kdenlive": (768, 3072)}
        text = self.tool.format_apps(apps)
        self.assertEqual(self.tool.parse_apps(text), (apps, []))
        self.assertIn("com.example.My_App-2 2560M 0\n", text)
        # (a line without its swap: the default; comments and spaces anywhere)
        self.assertEqual(self.tool.parse_apps("  org.a.B   2g # mine\n\t# just a comment\norg.c.D 300m\n"),
                         ({"org.a.B": (2048, 1024), "org.c.D": (300, 1024)}, []))

    def test_random_text_never_crashes_only_rejects(self):
        """Any text: the reader gives back apps it could read, each valid, and errors for the rest;
        what it reads cleanly, written again, reads back the same."""
        rnd = random.Random(20261103)
        words = ["org.mozilla.firefox", "org.a.B", "a.b", "x", "1.a", "org..a", "org.a-b.c", "org.a.b-c", "shared",
                 "SHARED", "5G", "512M", "0", "256M", "255M", "1048576M", "1048577M", "1024G", "1025G", "5 G", "5.5G",
                 "-1G", "0G", "05G", "G", "M", "#", "# x", "\t", " ", "\n", "\r\n", "\x00", "\u2028", "é.a", "org.é",
                 "\uff15G", "٣G", "9" * 40 + "M", "a" * 300 + ".b"]
        ids = ["org.mozilla.firefox", "org.a.B", "com.x_y.Z-2", "a.b", "org.a-b.c", "x", "1.a"]
        chars = "abcXYZ019._-# \t\nGMgm\x00é\u2028\x85"
        read = 0
        for _i in range(3000):
            mode = rnd.random()
            if mode < 0.4:       # (lines shaped like the file's, any word of the list in any place)
                text = "".join(" ".join(rnd.choice(ids if k == 0 and rnd.random() < 0.8 else words)
                                        for k in range(rnd.choice((1, 2, 2, 3, 3, 4)))) + "\n"
                               for _l in range(rnd.randint(0, 6)))
            elif mode < 0.7:
                text = "".join(rnd.choice(words) + rnd.choice([" ", " ", "\n", "\n"]) for _w in range(rnd.randint(0, 12)))
            else:
                text = "".join(rnd.choice(chars) for _c in range(rnd.randint(0, 80)))
            apps, errors = self.tool.parse_apps(text)
            self.assertIsInstance(errors, list)
            for app, v in apps.items():
                self.assertTrue(self.tool.valid_app(app), (text, app))
                if v is not None:
                    limit, swap = v
                    self.assertTrue(256 <= limit <= 1048576 and 0 <= swap <= 1048576, (text, v))
            again, errs = self.tool.parse_apps(self.tool.format_apps(apps))
            self.assertEqual((again, errs), (apps, []), text)
            read += bool(apps)
        self.assertGreater(read, 100)            # (the generator still makes lines worth reading)

    def test_random_apps_round_trip(self):
        rnd = random.Random(7)
        part = lambda: rnd.choice("abcXYZ_") + "".join(rnd.choice("abc019_") for _c in range(rnd.randint(0, 6)))
        for _i in range(500):
            apps = {}
            for _a in range(rnd.randint(0, 8)):
                app = ".".join(part() for _p in range(rnd.randint(2, 4))) + rnd.choice(["", "-x", "-2"])
                apps[app] = None if rnd.random() < 0.3 else (rnd.randint(256, 1048576), rnd.randint(0, 1048576))
            self.assertEqual(self.tool.parse_apps(self.tool.format_apps(apps)), (apps, []))

    def test_sizes(self):
        mib = self.tool.mib
        self.assertEqual([mib("5G"), mib("5g"), mib("512M"), mib("0"), mib("0", zero=True), mib("1024G"), mib("1025G")],
                         [5120, 5120, 512, None, 0, 1048576, None])
        for v in (256, 512, 1024, 2560, 5120, 1048576):
            self.assertEqual(mib(self.tool.size_text(v)), v)


if __name__ == "__main__":
    unittest.main()
