"""Shell helpers in lib/common.sh. Run: python3 -m unittest -v"""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(script, stdin="", **env):
    with tempfile.TemporaryDirectory() as home:      # common.sh creates folders in $HOME
        return subprocess.run(["bash", "-c", f"source {ROOT}/lib/common.sh 2>/dev/null; {script}"],
                              input=stdin, capture_output=True, text=True,
                              env={**os.environ, "HOME": home, **env}).stdout.strip()


class NewestTag(unittest.TestCase):
    TAGS = "v0.9.0\nv0.10.0\nv0.10.1-rc1\nv0.10.1-rc2\nfoo\n"

    def test_stable(self):
        self.assertEqual(sh("newest_tag", self.TAGS, FRAME_TWEAKS_CHANNEL="stable"), "v0.10.0")

    def test_beta_takes_latest_prerelease(self):
        self.assertEqual(sh("newest_tag", self.TAGS, FRAME_TWEAKS_CHANNEL="beta"), "v0.10.1-rc2")

    def test_beta_final_beats_its_prerelease(self):
        self.assertEqual(sh("newest_tag", "v1.0.0-rc1\nv1.0.0\n", FRAME_TWEAKS_CHANNEL="beta"), "v1.0.0")


class Pins(unittest.TestCase):
    def test_every_pin_is_complete(self):
        pins = [*ROOT.glob("packs/*/*/pin"), *ROOT.glob("packs/*/*/*.pin")]
        self.assertTrue(pins)                         # (tweaks moved into packs/: found where they are)
        for pin in pins:
            fields = dict(l.split("=", 1) for l in pin.read_text().splitlines() if "=" in l and not l.startswith("#"))
            self.assertTrue(fields.get("url", "").startswith("https://"), pin)
            if "rev" in fields:                       # a git commit
                self.assertRegex(fields["rev"], r"^[0-9a-f]{40}$", pin)
            else:                                     # a file, at a versioned URL
                self.assertRegex(fields.get("sha256", ""), r"^[0-9a-f]{64}$", pin)
                self.assertIn(fields.get("version", "?"), fields["url"], pin)

    def test_python_constraints_are_exact(self):
        for line in (ROOT / "lib" / "python-constraints.txt").read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                self.assertRegex(line, r"^[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*$")


@unittest.skipUnless(shutil.which("kwriteconfig6") and shutil.which("kreadconfig6"), "needs KDE's config tools")
class KConfig(unittest.TestCase):
    """save_kconfig / restore_kconfig: the keys go back as they were, a value (even one that looks
    like an option, -0.4) or unset. In a throwaway config folder; nothing is told over D-Bus."""

    def test_values_and_unset_keys_come_back(self):
        script = """f=frame-tweaks-testrc
            kwriteconfig6 --file $f --group Mouse --key Accel -- -0.4
            save_kconfig t $f Mouse Accel Speed
            kwriteconfig6 --file $f --group Mouse --key Accel 1; kwriteconfig6 --file $f --group Mouse --key Speed 3
            restore_kconfig t >/dev/null
            echo "$(kreadconfig6 --file $f --group Mouse --key Accel) $(kreadconfig6 --file $f --group Mouse --key Speed --default unset)"
        """
        with tempfile.TemporaryDirectory() as home:
            out = sh(script, XDG_CONFIG_HOME=f"{home}/.config", DBUS_SESSION_BUS_ADDRESS="disabled:")
        self.assertEqual(out, "-0.4 unset")


class QtVenv(unittest.TestCase):
    """remove_qt_venv: the PyQt6 venv shared by Arrow Pad, Screen snip, the NordVPN tray and the
    full installer window goes with the last of them, and stays on a reinstall."""
    SETUP = 'mkdir -p "$QT_VENV/bin" "$BIN" && touch "$QT_VENV/bin/python"; '

    def left(self, setup="", **env):
        return sh(self.SETUP + setup + ' remove_qt_venv >/dev/null; [ -d "$QT_VENV" ] && echo kept || echo removed', **env)

    def test_the_last_one_removes_it(self):
        self.assertEqual(self.left(), "removed")

    def test_kept_for_the_installer_window(self):     # (it runs on the venv as bin/sft-python)
        self.assertEqual(self.left('touch "$QT_VENV/bin/sft-python";'), "kept")

    def test_kept_while_another_tweak_uses_it(self):
        self.assertEqual(self.left('printf "#!/bin/sh\\n" > "$BIN/frame-snip"; chmod +x "$BIN/frame-snip";'), "kept")

    def test_kept_on_a_reinstall(self):
        self.assertEqual(self.left(FRAME_TWEAKS_REINSTALL="1"), "kept")


class Bashrc(unittest.TestCase):
    """ensure_path (and need_brew, after installing Homebrew) add their line to ~/.bashrc once, on
    a line of its own: to a file whose last line had no newline it was glued onto that line, and
    then found there, so it stayed broken."""
    LINE = 'export PATH="$HOME/.local/bin:$PATH"'

    def bashrc(self, before):
        return sh(f"{before}; ensure_path; ensure_path; cat ~/.bashrc; echo END")

    def test_after_a_last_line_without_a_newline(self):
        self.assertEqual(self.bashrc("printf 'alias ll=\"ls -l\"' > ~/.bashrc"), f'alias ll="ls -l"\n{self.LINE}\nEND')

    def test_after_a_last_line_with_one(self):
        self.assertEqual(self.bashrc("printf 'alias ll=\"ls -l\"\\n' > ~/.bashrc"), f'alias ll="ls -l"\n{self.LINE}\nEND')

    def test_empty_or_none(self):
        self.assertEqual(self.bashrc(": > ~/.bashrc"), f"{self.LINE}\nEND")
        self.assertEqual(self.bashrc("rm -f ~/.bashrc"), f"{self.LINE}\nEND")



class DesktopEntry(unittest.TestCase):
    """install_desktop writes a menu entry whole, in English when translating it fails: piped
    straight from lib/i18n.py, a failure there left the entry empty (and, with pipefail, stopped
    the tweak's install). (Stand-ins: python3 fails only for that; nothing real is started.)"""
    def test_whole_in_english_when_translating_fails(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            stubs, home = d / "stubs", d / "home"
            stubs.mkdir()
            home.mkdir()
            for name, body in (("systemctl", "exit 0"), ("update-desktop-database", "exit 0"),
                               ("python3", 'case "$*" in *"i18n.py desktop"*) exit 1 ;; esac; exec /usr/bin/python3 "$@"')):
                (stubs / name).write_text(f"#!/bin/bash\n{body}\n")
                (stubs / name).chmod(0o755)
            desktop = d / "thing.desktop"
            desktop.write_text("[Desktop Entry]\nType=Application\nName=Thing\nExec=@BIN@/thing\n")
            r = subprocess.run(["bash", "-c", f'source {ROOT}/lib/common.sh; install_desktop "{desktop}"'],
                               capture_output=True, text=True, timeout=60,
                               env={**os.environ, "HOME": str(home), "PATH": f"{stubs}:{os.environ['PATH']}"})
            self.assertEqual(r.returncode, 0, r.stderr)
            text = (home / ".local/share/applications/thing.desktop").read_text()
            self.assertIn("Name=Thing", text)
            self.assertIn(f"Exec={home}/.local/bin/thing", text)


class SteamVRRestart(unittest.TestCase):
    """status_restart: a status line the installer window turns into ⟳ Restart SteamVR. vr_started_before:
    has the running SteamVR started since a file changed (with pgrep and ps stand-ins)?"""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.file = self.dir / "installed"
        self.file.write_text("1.0\n")

    def started_before(self, running=True, age=100, file_age=0):
        for name, body in (("pgrep", 'echo 4242' if running else 'exit 1'), ("ps", f'echo "  {age}"')):
            (self.dir / name).write_text(f"#!/bin/sh\n{body}\n")
            (self.dir / name).chmod(0o755)
        if self.file.exists():
            os.utime(self.file, (time.time() - file_age,) * 2)
        return sh(f'vr_started_before "{self.file}" && echo yes || echo no', PATH=f"{self.dir}:/usr/bin:/bin")

    def test_started_before(self):
        self.assertEqual(self.started_before(), "yes")                      # installed after SteamVR started
        self.assertEqual(self.started_before(file_age=200), "no")           # SteamVR started since
        self.assertEqual(self.started_before(running=False), "no")
        self.file.unlink()
        self.assertEqual(self.started_before(), "no")

    def test_status_line(self):
        r = subprocess.run(["bash", "-c", f"source {ROOT}/lib/common.sh 2>/dev/null; status_restart 'Load it'; echo after"],
                           capture_output=True, text=True, env={**os.environ, "HOME": str(self.dir)})
        self.assertEqual((r.returncode, r.stdout), (2, "restart  Load it\n"))      # (2: needs attention)



class DashboardPatchInstalled(unittest.TestCase):
    """install_dashboard_patch while SteamVR's patches service runs: "Active now." only once the
    service has injected the patch (it said so after its 10 checks either way); otherwise what the
    service says. In a throwaway home, with stand-ins for the service and systemctl."""

    def install(self, status):
        with tempfile.TemporaryDirectory() as home:
            d = Path(home) / ".local/share/frame-tweaks/vr-dashboard"
            d.mkdir(parents=True)
            (d / "sft-dashboard").write_text(f"#!/bin/sh\n[ -n '{status}' ] && echo '{status}'\n"
                                             f"[ '{status}' = 'curvature: patched' ]\n")
            (d / "sft-dashboard").chmod(0o755)
            (Path(home) / "stubs").mkdir()
            (Path(home) / "stubs/systemctl").write_text("#!/bin/sh\nexit 3\n")    # (never the real one)
            (Path(home) / "stubs/systemctl").chmod(0o755)
            (Path(home) / "patch.js").write_text("")
            script = (f"source {ROOT}/lib/common.sh 2>/dev/null; "
                      'sysctl_user() { [ "$3" = sft-dashboard.service ]; }; sleep() { :; }; '   # (it runs; no waiting)
                      f"install_dashboard_patch curvature {home}/patch.js")
            env = {"HOME": home, "PATH": f"{home}/stubs:/usr/bin:/bin", "LANG": "C.UTF-8",
                   "FRAME_TWEAKS_LANGUAGE": "en", "FRAME_TWEAKS_LANG_RESOLVED": "en"}
            r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout

    def test_says_active_only_once_it_is(self):
        self.assertIn("Active now.", self.install("curvature: patched"))
        out = self.install("curvature: port open, not patched yet")
        self.assertNotIn("Active now.", out)
        self.assertIn("Not active yet: curvature: port open, not patched yet", out)
        out = self.install("curvature: SteamVR changed (missing: a thing); off")
        self.assertIn("Not active yet: curvature: SteamVR changed (missing: a thing); off", out)
        self.assertIn("Not active yet: the dashboard patch service did not answer", self.install(""))


if __name__ == "__main__":
    unittest.main()
