"""VR memory guard (packs/core/vr-memory-guard): install gives desktop apps (app.slice) a limit of
the device's memory minus the reserve for VR, every Firefox scope its own, and SteamVR the lowest
OOM score a user service may have; it sets the running slice and Firefox at once; it refuses a
reserve that leaves too little and a size it can't read; uninstall lifts the limits and keeps the
settings; the status line reads the slice's limit and use. A fake /proc/meminfo and cgroup folder
stand in for the Frame's."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TWEAK = ROOT / "packs/core/vr-memory-guard"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402

DROPIN = "frame-tweaks-vr-memory-guard.conf"


class VrMemoryGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.meminfo = self.home / "meminfo"
        self.meminfo.write_text("MemTotal:       16037888 kB\nMemFree:  1000 kB\n")   # (15662 MiB, the Frame's)
        self.calls = self.home / "systemctl.log"
        self.stubs = self.home / "stubs"
        # systemctl: logs its arguments; one running Firefox scope; SteamVR running.
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

    def run_script(self, name, ok=True):
        r = subprocess.run(["bash", str(TWEAK / name)], env=self.env, capture_output=True, text=True, timeout=30)
        if ok is not None:
            self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return r

    def dropin(self, unit):
        return (self.units / f"{unit}.d" / DROPIN).read_text()

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
        self.assertIn("desktop apps 1900 of 10542 MB", r.stdout)
        (self.cg / "cgroup.controllers").write_text("cpu pids\n")
        self.assertEqual(self.run_script("status.sh", ok=None).returncode, 2)


if __name__ == "__main__":
    unittest.main()
