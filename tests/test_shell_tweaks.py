"""Shell tweaks with no other tests, run in a throwaway home with stand-ins for system tools:
Firefox's user.js block (install, the old marker, uninstall resetting prefs.js) and NordVPN's
status line; pinned downloads falling back to Frame Tweaks' copy."""
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.stubs = self.home / "stubs"
        self.stubs.mkdir()

    def stub(self, name, body):
        (self.stubs / name).write_text(f"#!/bin/bash\n{body}\n")
        (self.stubs / name).chmod(0o755)

    def run_script(self, script, *args):
        env = {"HOME": str(self.home), "PATH": f"{self.stubs}:/usr/bin:/bin", "USER": os.environ.get("USER", "u")}
        return subprocess.run(["bash", str(ROOT / "packs/official" / script), *args], env=env, capture_output=True, text=True, timeout=60)


class Firefox(Home):
    def setUp(self):
        super().setUp()
        root = self.home / ".var/app/org.mozilla.firefox/.mozilla/firefox"
        self.profile = root / "abc.default-release"
        self.profile.mkdir(parents=True)
        (root / "installs.ini").write_text("[X]\nDefault=abc.default-release\n")
        self.stub("pgrep", "exit 1")                      # Firefox isn't running

    def test_install_replaces_old_block_and_keeps_yours(self):
        (self.profile / "user.js").write_text('user_pref("mine", 1);\n// >>> steam-frame-tweaks\n'
                                              'user_pref("old", 1);\n// <<< steam-frame-tweaks\n')
        r = self.run_script("firefox/install.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        js = (self.profile / "user.js").read_text()
        self.assertIn('user_pref("mine", 1);', js)
        self.assertNotIn("steam-frame-tweaks", js)
        self.assertNotIn('"old"', js)
        self.assertEqual(js.count("// >>> frame-tweaks"), 1)
        self.assertIn("privacy.resistFingerprinting", js)
        self.assertNotEqual(self.run_script("firefox/status.sh").returncode, 1)     # installed (restart to apply)

    def test_uninstall_resets_our_prefs_in_prefs_js(self):
        self.run_script("firefox/install.sh")
        (self.profile / "prefs.js").write_text('user_pref("privacy.resistFingerprinting", true);\n'
                                               'user_pref("browser.startup.page", 3);\n')
        r = self.run_script("firefox/uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("frame-tweaks", (self.profile / "user.js").read_text())
        prefs = (self.profile / "prefs.js").read_text()
        self.assertNotIn("resistFingerprinting", prefs)
        self.assertIn("browser.startup.page", prefs)              # not ours: kept
        self.assertTrue((self.profile / "prefs.js.frame-tweaks-bak").exists())

    def test_uninstall_leaves_prefs_js_while_firefox_runs(self):
        self.run_script("firefox/install.sh")
        (self.profile / "prefs.js").write_text('user_pref("privacy.resistFingerprinting", true);\n')
        self.stub("pgrep", "exit 0")
        r = self.run_script("firefox/uninstall.sh")
        self.assertIn("Firefox is running", r.stderr + r.stdout)
        self.assertIn("resistFingerprinting", (self.profile / "prefs.js").read_text())


class NordVPNStatus(Home):
    def setUp(self):
        super().setUp()
        (self.home / ".local/bin").mkdir(parents=True)
        self.stub_file = self.home / ".local/bin/nordvpn-wg"
        self.stub_file.write_text("#!/bin/sh\n")
        self.stub_file.chmod(0o755)
        (self.home / ".config/nordvpn-wg").mkdir(parents=True)
        (self.home / ".config/nordvpn-wg/private_key").write_text("x")

    def nmcli(self, connections, active=""):
        self.stub("nmcli", f'if [ "$*" = "-t -f TYPE,NAME connection show --active" ]; then printf "{active}"; '
                           f'else printf "{connections}"; fi')

    def test_no_locations_is_still_installed(self):
        self.nmcli("802-11-wireless:Home\\n")
        r = self.run_script("nordvpn/status.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 location(s); disconnected", r.stdout)

    def test_counts_locations_and_shows_the_active_one(self):
        self.nmcli("wireguard:NordVPN Canada\\nwireguard:NordVPN Japan\\n", "wireguard:NordVPN Japan\\n")
        r = self.run_script("nordvpn/status.sh")
        self.assertIn("2 location(s); connected via Japan", r.stdout)


class PinnedDownload(Home):
    """fetch_pinned: upstream's file if it's there and unchanged, else the pin's mirror= copy,
    held to the same sha256."""
    GOOD = b"the pinned file\n"

    def fetch(self, upstream, mirror=None, with_mirror=True):
        repo = self.home / "repo"
        (repo / "packs/official/x").mkdir(parents=True, exist_ok=True)
        pin = ["url=https://up.example/f.bin", f"sha256={hashlib.sha256(self.GOOD).hexdigest()}"]
        if with_mirror:
            pin.append("mirror=https://mirror.example/f.bin")
        (repo / "packs/official/x/pin").write_text("\n".join(pin) + "\n")
        files = self.home / "files"
        files.mkdir(exist_ok=True)
        for name, data in (("up", upstream), ("mirror", mirror)):
            if data is not None:
                (files / name).write_bytes(data)
        # curl -fL# -o OUT URL: copy the matching file, or fail like a 404
        self.stub("curl", f'out=$3; case "$4" in *up.example*) f={files}/up ;; *) f={files}/mirror ;; esac\n'
                          '[ -f "$f" ] && cp "$f" "$out" || exit 22')
        env = {"HOME": str(self.home), "PATH": f"{self.stubs}:/usr/bin:/bin"}
        out = self.home / "out"
        r = subprocess.run(["bash", "-c", f'source {ROOT}/lib/common.sh; REPO_DIR={repo}; fetch_pinned x {out}'],
                           env=env, capture_output=True, text=True, timeout=30)
        return r, (out.read_bytes() if out.exists() else None)

    def test_upstream_file_is_used(self):
        r, got = self.fetch(self.GOOD, mirror=b"never read")
        self.assertEqual((r.returncode, got), (0, self.GOOD))
        self.assertNotIn("copy", r.stderr)

    def test_gone_upstream_falls_back_to_the_copy(self):
        r, got = self.fetch(None, mirror=self.GOOD)
        self.assertEqual((r.returncode, got), (0, self.GOOD), r.stderr)
        self.assertIn("using Frame Tweaks' copy", r.stderr)

    def test_changed_upstream_falls_back_to_the_copy(self):
        r, got = self.fetch(b"something else", mirror=self.GOOD)
        self.assertEqual((r.returncode, got), (0, self.GOOD), r.stderr)

    def test_a_changed_copy_is_refused_too(self):
        r, _ = self.fetch(None, mirror=b"tampered")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not installing it", r.stderr)

    def test_no_copy_no_fallback(self):
        r, _ = self.fetch(b"something else", with_mirror=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("differs from the pinned file", r.stderr)


if __name__ == "__main__":
    unittest.main()
