"""packs/core/ydotool/install.sh with Arch Linux ARM's package served by a stand-in curl (gpgv a
stand-in too: test_alarm_fetch checks the signature for real): a new build is installed only if
both programs load here and ydotool starts from where it was unpacked (its --help); otherwise the
working ydotool from before stays, or, with none, the install stops. (A build for another
machine, which ldd calls "not a dynamic executable", replaced a working ydotool: Dictation and
Arrow Pad couldn't type any more.) In a throwaway home; systemctl is a stand-in, nothing starts."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
TOOLS = ("bsdtar", "vercmp", "ldd", "true", "false")
MIRROR = "http://mirror.test/aarch64"
VERSION = next(line.split("=", 1)[1] for line in (ROOT / "lib/tested-versions").read_text().splitlines()
               if line.startswith("ydotool="))
CURL = """out=""; url=""
while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift ;; http*) url=$1 ;; esac; shift; done
case $url in "$MIRROR"/*) rel=${url#"$MIRROR"/} ;; *) exit 22 ;; esac
if [[ $rel == */ ]]; then f="$SERVE/${rel%/}/listing.html"; else f="$SERVE/$rel"; fi
[ -f "$f" ] || exit 22
if [ -n "$out" ]; then cp "$f" "$out"; else cat "$f"; fi"""


@unittest.skipUnless(all(shutil.which(t) for t in TOOLS), f"needs {', '.join(TOOLS)}")
class YdotoolInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.home, self.serve, self.stubs = t / "home", t / "serve", t / "stubs"
        self.home.mkdir()
        (self.serve / "extra").mkdir(parents=True)
        stub(self.stubs, "curl", CURL)
        stub(self.stubs, "gpgv", "exit 0")
        stub(self.stubs, "systemctl", 'case " $* " in *" is-active "*) exit 3 ;; esac')
        self.uinput = t / "uinput"
        self.uinput.touch()
        self.bin = self.home / ".local/bin"
        self.works = Path(shutil.which("true")).resolve().read_bytes()     # (loads here; --help: exit 0)
        self.fails = Path(shutil.which("false")).resolve().read_bytes()    # (loads; --help: exit 1)
        arm = bytearray(self.works)
        arm[4], arm[18:20] = 1, (40).to_bytes(2, "little")                  # (32-bit ARM, as armv7h)
        self.other_machine = bytes(arm)

    def package(self, ydotool, ydotoold):
        build = Path(self.tmp.name) / "build"
        shutil.rmtree(build, ignore_errors=True)
        (build / "usr/bin").mkdir(parents=True)
        (build / ".PKGINFO").write_text(f"pkgname = ydotool\npkgver = {VERSION}\narch = aarch64\n")
        for name, data in (("ydotool", ydotool), ("ydotoold", ydotoold)):
            (build / "usr/bin" / name).write_bytes(data)
            (build / "usr/bin" / name).chmod(0o755)
        name = f"ydotool-{VERSION}-aarch64.pkg.tar.zst"
        subprocess.run(["bsdtar", "-caf", str(self.serve / "extra" / name), "-C", str(build), ".PKGINFO", "usr"],
                       check=True, timeout=30)
        (self.serve / "extra" / f"{name}.sig").write_bytes(b"")
        (self.serve / "extra/listing.html").write_text(f'<a href="{name}">{name}</a>\n')

    def installed_before(self):
        self.bin.mkdir(parents=True)
        for name in ("ydotool", "ydotoold"):
            (self.bin / name).write_bytes(self.works)
            (self.bin / name).chmod(0o755)

    def install(self):
        path = [os.path.dirname(shutil.which(t)) for t in TOOLS] + ["/usr/bin", "/bin"]
        env = sandbox_env(self.home, self.stubs, path=path, ALARM_MIRROR=MIRROR, MIRROR=MIRROR, SERVE=self.serve,
                          FRAME_TWEAKS_UINPUT=self.uinput, FRAME_TWEAKS_LIB=ROOT / "lib")
        return subprocess.run(["bash", str(ROOT / "packs/core/ydotool/install.sh")], env=env,
                              capture_output=True, text=True, timeout=120)

    def test_a_build_that_runs_is_installed(self):
        self.package(self.works, self.works)
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.bin / "ydotoold").read_bytes(), self.works)

    def test_a_build_for_another_machine_leaves_the_working_one(self):
        self.installed_before()
        self.package(self.other_machine, self.other_machine)
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("doesn't run on this SteamOS (not a dynamic executable); keeping the one you have.", r.stderr)
        for name in ("ydotool", "ydotoold"):
            self.assertEqual((self.bin / name).read_bytes(), self.works, name)

    def test_a_ydotool_that_doesnt_start_leaves_the_working_one(self):
        self.installed_before()
        self.package(self.fails, self.works)
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("doesn't run on this SteamOS (ydotool didn't start); keeping the one you have.", r.stderr)
        self.assertEqual((self.bin / "ydotool").read_bytes(), self.works)

    def test_with_none_before_the_install_stops(self):
        self.package(self.works, self.other_machine)
        r = self.install()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Arch Linux ARM's current ydotool doesn't run on this SteamOS (not a dynamic executable).",
                      r.stderr)
        self.assertFalse((self.bin / "ydotoold").exists())


if __name__ == "__main__":
    unittest.main()
