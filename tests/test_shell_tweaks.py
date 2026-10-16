"""Shell tweaks with no other tests, run in a throwaway home with stand-ins for system tools:
Firefox's user.js block (install, the old marker, uninstall resetting prefs.js, status without a
default profile) and NordVPN's status line; Shared clipboard's status with and without desktop
mode, and from an older build; Mouse cursor fix not needed from gamescope 3.16.30; pinned
downloads falling back to Frame Tweaks' copy; Arrow Pad's uninstall giving a pad it asked to quit
the time to close."""
import sys
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402


class Home(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.stubs = self.home / "stubs"
        self.stubs.mkdir()

    def stub(self, name, body):
        stub(self.stubs, name, body)

    def run_script(self, script, *args):
        env = sandbox_env(self.home, self.stubs)
        return subprocess.run(["bash", str(next(p for p in ROOT.glob("packs/*/" + script))), *args], env=env, capture_output=True, text=True, timeout=60)


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

    def test_status_without_a_default_profile(self):
        """installs.ini names no default profile: not installed, through status_missing (the check
        stopped at a failing command, which now counts as "status check failed")."""
        (self.profile.parent / "installs.ini").write_text("[X]\n")
        r = self.run_script("firefox/status.sh")
        self.assertEqual((r.returncode, r.stdout.strip()), (1, "missing  no Firefox (Flathub) profile"))

    def test_uninstall_leaves_prefs_js_while_firefox_runs(self):
        self.run_script("firefox/install.sh")
        (self.profile / "prefs.js").write_text('user_pref("privacy.resistFingerprinting", true);\n')
        self.stub("pgrep", "exit 0")
        r = self.run_script("firefox/uninstall.sh")
        self.assertIn("Firefox is running", r.stderr + r.stdout)
        self.assertIn("resistFingerprinting", (self.profile / "prefs.js").read_text())

    def test_uninstall_puts_back_what_you_had_set_yourself(self):
        """Settings of ours you had set yourself before installing (HTTPS-only mode, strict
        tracking protection, an English-pages choice of your own) are put back as they were,
        not reset to Firefox's defaults; an update (install run again, with Firefox's copies of
        ours in prefs.js by then) doesn't take ours for yours."""
        mine = ['user_pref("browser.contentblocking.category", "strict");',
                'user_pref("dom.security.https_only_mode", true);', 'user_pref("privacy.spoof_english", 1);']
        prefs = self.profile / "prefs.js"
        prefs.write_text("\n".join(['user_pref("browser.startup.page", 3);', *mine]) + "\n")
        self.assertEqual(self.run_script("firefox/install.sh").returncode, 0)
        # Firefox ran: it wrote ours into prefs.js (its English-pages value over yours)
        prefs.write_text('user_pref("browser.contentblocking.category", "strict");\n'
                         'user_pref("browser.startup.page", 3);\n'
                         'user_pref("dom.security.https_only_mode", true);\n'
                         'user_pref("privacy.resistFingerprinting", true);\n'
                         'user_pref("privacy.spoof_english", 2);\n')
        self.assertEqual(self.run_script("firefox/install.sh").returncode, 0)     # (an update)
        r = self.run_script("firefox/uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        after = prefs.read_text().splitlines()
        self.assertNotIn('user_pref("privacy.resistFingerprinting", true);', after)
        self.assertNotIn('user_pref("privacy.spoof_english", 2);', after)
        for line in ['user_pref("browser.startup.page", 3);', *mine]:
            self.assertEqual(after.count(line), 1, after)
        # Installed again later: what's there then is recorded afresh, and put back the same way
        prefs.write_text('user_pref("dom.security.https_only_mode", true);\n')
        self.run_script("firefox/install.sh")
        prefs.write_text('user_pref("dom.security.https_only_mode", true);\n'
                         'user_pref("privacy.resistFingerprinting", true);\n')
        self.run_script("firefox/uninstall.sh")
        self.assertEqual(prefs.read_text(), 'user_pref("dom.security.https_only_mode", true);\n')

    def test_installed_before_its_record_existed_resets_them_all(self):
        """Installed by a version that didn't record yours: an update finds Firefox's copies of
        ours in prefs.js and can't tell them from yours, so removing resets them all, as before."""
        (self.profile / "user.js").write_text("// >>> frame-tweaks\n// <<< frame-tweaks\n")
        prefs = self.profile / "prefs.js"
        prefs.write_text('user_pref("dom.security.https_only_mode", true);\n'
                         'user_pref("privacy.resistFingerprinting", true);\n')
        self.assertEqual(self.run_script("firefox/install.sh").returncode, 0)     # (the update)
        self.assertEqual(self.run_script("firefox/uninstall.sh").returncode, 0)
        self.assertEqual(prefs.read_text(), "")


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
        """connections: TYPE:AUTOCONNECT:NAME lines; active: TYPE:NAME lines."""
        self.stub("nmcli", f'if [ "$*" = "-t -f TYPE,NAME connection show --active" ]; then printf "{active}"; '
                           f'elif [ "$*" = "-t -f TYPE,AUTOCONNECT,NAME connection show" ]; then printf "{connections}"; '
                           'else exit 1; fi')

    def test_no_locations_is_still_installed(self):
        self.nmcli("802-11-wireless:yes:Home\\n")
        r = self.run_script("nordvpn/status.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 location(s); disconnected", r.stdout)

    def test_counts_locations_and_shows_the_active_one(self):
        self.nmcli("wireguard:no:NordVPN Canada\\nwireguard:no:NordVPN Japan\\n802-11-wireless:yes:Home\\n",
                   "wireguard:NordVPN Japan\\n")
        r = self.run_script("nordvpn/status.sh")
        self.assertEqual(r.stdout.strip(), "ok       2 location(s); connected via Japan")

    def test_says_which_location_connects_at_startup(self):
        # (nordvpn-wg autoconnect: NetworkManager's autoconnect on that one; the Wi-Fi's isn't ours)
        conns = "802-11-wireless:yes:Home\\nwireguard:no:NordVPN Canada\\nwireguard:yes:NordVPN United States\\n"
        self.nmcli(conns, "wireguard:NordVPN Canada\\n")
        r = self.run_script("nordvpn/status.sh")
        self.assertEqual(r.stdout.strip(), "ok       2 location(s); connected via Canada; connects at startup: United States")
        self.nmcli(conns)
        r = self.run_script("nordvpn/status.sh")
        self.assertEqual(r.stdout.strip(), "ok       2 location(s); disconnected; connects at startup: United States")


class CursorNotNeeded(Home):
    """Mouse cursor fix: not needed from gamescope 3.16.30 (SteamVR draws desktop mode's pointer
    itself); installed there, its status asks to uninstall it. (pacman is a stand-in.)"""
    def gamescope(self, version):
        self.stub("pacman", f'[ "$*" = "-Q gamescope" ] && echo "gamescope {version}"')

    def test_needed_before_gamescope_3_16_30_only(self):
        for version, needed in (("3.16.28-2", True), ("3.16.29-1", True), ("3.16.30-1", False), ("3.16.31-1", False),
                                ("3.17.0-1", False), ("3.16.3-1", True)):
            self.gamescope(version)
            r = self.run_script("cursor/needed.sh")
            self.assertEqual(r.returncode, 0 if needed else 1, version)
            if not needed:
                self.assertIn(f"this Frame has {version}", r.stdout)
        self.stub("pacman", "exit 1")                      # (no pacman, or no gamescope: offered)
        self.assertEqual(self.run_script("cursor/needed.sh").returncode, 0)

    def test_installed_where_not_needed_is_a_warning(self):
        conf = self.home / ".config/environment.d/90-kwin-software-cursor.conf"
        conf.parent.mkdir(parents=True)
        conf.write_text("KWIN_FORCE_SW_CURSOR=1\n")
        self.stub("pgrep", "exit 1")                       # (no desktop mode running)
        self.gamescope("3.16.30-1")
        r = self.run_script("cursor/status.sh")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("second pointer (a black X): uninstall it", r.stdout)
        self.gamescope("3.16.28-2")
        r = self.run_script("cursor/status.sh")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "ok       installed (active in desktop mode after a reboot)"))


class ClipboardStatus(Home):
    """clipboard-sync starts with desktop mode: not running without it is as it should be; not
    running with it is a warning (Restart starts it). (pgrep is a stand-in.)"""
    def status(self, running, desktop):
        b = self.home / ".local/bin"
        b.mkdir(parents=True, exist_ok=True)
        (b / "clipboard-sync").write_text("#!/bin/sh\n")
        (b / "clipboard-sync").chmod(0o755)
        self.stub("pgrep", f'case "$*" in *clipboard-sync*) {"echo 42" if running else "exit 1"} ;; '
                           f'*ksmserver*) {"echo 7" if desktop else "exit 1"} ;; esac')
        r = self.run_script("clipboard/status.sh")
        return r.returncode, r.stdout.strip()

    def test_not_running_without_desktop_mode_is_fine(self):
        self.assertEqual(self.status(False, False), (0, "ok       installed; starts with desktop mode"))

    def test_not_running_with_desktop_mode_is_a_warning(self):
        self.assertEqual(self.status(False, True), (2, "warning  not running, though desktop mode is (Restart starts it)"))

    def test_running_says_its_version(self):
        v = self.home / ".local/share/frame-tweaks/clipboard-sync/VERSION"
        v.parent.mkdir(parents=True)
        v.write_text("0.3.0\n")
        self.assertEqual(self.status(True, True), (0, "ok       clipboard-sync 0.3.0 running"))

    def test_an_older_build_running_says_what_it_lacks(self):
        """Built by an older Frame Tweaks (no VERSION file, as one still running from then): the
        check stopped where it read that file, without a word, and the tweak read as not installed."""
        self.assertEqual(self.status(True, True), (2, "warning  older build: replaces copied images with text (Reinstall fixes it)"))
        patched = self.home / ".local/share/frame-tweaks/src/clipboard-sync/.sft-patched"
        patched.parent.mkdir(parents=True)
        patched.write_text("keep-images\nsync-sessions\n")
        self.assertEqual(self.status(True, True), (0, "ok       clipboard-sync running"))


class PinnedDownload(Home):
    """fetch_pinned: upstream's file if it's there and unchanged, else the pin's mirror= copy,
    held to the same sha256."""
    GOOD = b"the pinned file\n"

    def fetch(self, upstream, mirror=None, with_mirror=True):
        repo = self.home / "repo"
        (repo / "packs/core/x").mkdir(parents=True, exist_ok=True)
        pin = ["url=https://up.example/f.bin", f"sha256={hashlib.sha256(self.GOOD).hexdigest()}"]
        if with_mirror:
            pin.append("mirror=https://mirror.example/f.bin")
        (repo / "packs/core/x/pin").write_text("\n".join(pin) + "\n")
        files = self.home / "files"
        files.mkdir(exist_ok=True)
        for name, data in (("up", upstream), ("mirror", mirror)):
            if data is not None:
                (files / name).write_bytes(data)
        # curl -fL# -o OUT URL: copy the matching file, or fail like a 404
        self.stub("curl", f'out=$3; case "$4" in *up.example*) f={files}/up ;; *) f={files}/mirror ;; esac\n'
                          '[ -f "$f" ] && cp "$f" "$out" || exit 22')
        env = sandbox_env(self.home, self.stubs)
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



class ArrowPadUninstall(Home):
    """Uninstalling asks a running pad to quit (it lets go of its keys and SteamVR as it closes),
    then stops what's still running: it looked at once, and stopped a pad in the middle of closing."""

    def setUp(self):
        super().setUp()
        self.log = self.home / "calls.log"
        stub(self.home / ".local/bin", "arrowpad", f'echo "arrowpad $*" >> "{self.log}"')
        self.stub("pkill", f'echo "pkill $*" >> "{self.log}"')
        self.stub("update-desktop-database", "exit 0")

    def uninstall(self, closes_after):
        """A pad that's still there for its first `closes_after` looks (pgrep), or never (None)."""
        n = self.home / "looks"
        self.stub("pgrep", f'echo x >> "{n}"; ' + ("exit 0" if closes_after is None else
                                                  f'[ "$(wc -l < "{n}")" -le {closes_after} ]'))
        r = self.run_script("arrowpad/uninstall.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.log.read_text()

    def test_a_pad_that_quits_isnt_stopped(self):
        log = self.uninstall(closes_after=5)                 # (half a second)
        self.assertIn("arrowpad --quit --desktop", log)
        self.assertNotIn("pkill", log)

    def test_one_that_doesnt_is(self):
        log = self.uninstall(closes_after=None)
        self.assertIn("pkill -f ^", log)


if __name__ == "__main__":
    unittest.main()
