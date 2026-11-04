"""lib/common.sh heal_venvs: Frame Tweaks' venvs moved to SteamOS's Python when an update changes
it (SteamOS 0.5.7's beta: 3.12 to 3.14, every package gone at once). Run: python3 -m unittest -v"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = "%d.%d" % sys.version_info[:2]


def sh(home, script, **env):
    return subprocess.run(["bash", "-c", f"source {ROOT}/lib/common.sh 2>/dev/null; {script}"],
                          capture_output=True, text=True,
                          env={**os.environ, "HOME": str(home), "FRAME_TWEAKS_PYTHON": sys.executable, **env})


def old_venv(where, version="3.0", compiled=False):
    """A venv as an older Python left it: pyvenv.cfg, and one package asked for (pkgx) in
    lib/python<version>/site-packages, with what it pulled in (dep, not REQUESTED)."""
    (where / "bin").mkdir(parents=True)
    (where / "pyvenv.cfg").write_text(f"home = /usr/bin\nversion = {version}.1\n")
    site = where / f"lib/python{version}/site-packages"
    for name, requested in (("pkgx", True), ("dep", False)):
        (site / name).mkdir(parents=True)
        (site / name / "__init__.py").write_text(f"NAME = {name!r}\n")
        info = site / f"{name}-1.0.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n")
        (info / "top_level.txt").write_text(name + "\n")
        if requested:
            (info / "REQUESTED").write_text("")
    if compiled:
        (site / "pkgx" / f"_speed.cpython-{version.replace('.', '')}-aarch64-linux-gnu.so").write_bytes(b"")
    return where


class Stale(unittest.TestCase):
    def test_a_venv_for_another_python_is_stale(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v")
            self.assertEqual(sh(home, f"venv_python_version {v}").stdout.strip(), "3.0")
            self.assertEqual(sh(home, f"venv_stale {v}").returncode, 0)

    def test_one_for_this_python_is_not(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", NOW)
            self.assertNotEqual(sh(home, f"venv_stale {v}").returncode, 0)

    def test_no_venv_is_not(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertNotEqual(sh(home, f"venv_stale {home}/none").returncode, 0)


class Heal(unittest.TestCase):
    # (pip_pinned stubbed: it would need PyPI; it logs what it was asked for, and fails)
    PIP = 'pip_pinned() { shift; echo "$*" >> "$HOME/pip.log"; return 1; }; '

    def test_pure_packages_move_offline(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v")
            r = sh(home, self.PIP + f"heal_venv {v}")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((Path(home) / "pip.log").exists())      # (no PyPI needed)
            self.assertEqual(sh(home, f"venv_python_version {v}").stdout.strip(), NOW)
            out = subprocess.run([str(v / "bin/python"), "-c", "import pkgx, dep; print(pkgx.NAME, dep.NAME)"],
                                 capture_output=True, text=True)
            self.assertEqual(out.stdout.split(), ["pkgx", "dep"], out.stderr)
            self.assertFalse(list(Path(home).glob("v.heal.*")))     # (nothing left beside it)

    def test_a_part_compiled_for_one_python_is_installed_again(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", compiled=True)
            r = sh(home, self.PIP + f"heal_venv {v}")
            self.assertNotEqual(r.returncode, 0)                       # (the stub fails: so does the heal)
            self.assertEqual((Path(home) / "pip.log").read_text().split(), ["pkgx"])   # (only what was asked for)
            self.assertEqual(sh(home, f"venv_python_version {v}").stdout.strip(), NOW)

    def test_a_heal_whose_pip_failed_is_tried_again(self):
        # (SteamOS 3.12 to 3.14 at a login before the Wi-Fi is up: the venv was made anew on the
        # new Python and the old packages went, so it looked current and was never retried)
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", compiled=True)
            r = sh(home, self.PIP + f"ft_venvs() {{ echo {v}; }}; heal_units() {{ :; }}; heal_venvs")
            self.assertNotEqual(r.returncode, 0)                       # (offline: pip failed)
            self.assertEqual(sh(home, f"venv_stale {v}").returncode, 0, "a failed heal must stay stale")
            ok = 'pip_pinned() { shift; echo "$*" >> "$HOME/pip.log"; return 0; }; '
            r = sh(home, ok + f"ft_venvs() {{ echo {v}; }}; heal_units() {{ :; }}; heal_venvs")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((Path(home) / "pip.log").read_text().split(), ["pkgx", "pkgx"])   # (tried, then again)
            self.assertNotEqual(sh(home, f"venv_stale {v}").returncode, 0)            # (done: current now)
            r = sh(home, self.PIP + f"ft_venvs() {{ echo {v}; }}; heal_venvs")
            self.assertEqual((r.returncode, r.stdout), (0, ""))                       # (and left alone)

    def test_heal_venvs_leaves_a_current_venv(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", NOW)
            before = sorted(p.name for p in (v / f"lib/python{NOW}/site-packages").iterdir())
            r = sh(home, self.PIP + f"ft_venvs() {{ echo {v}; }}; heal_venvs")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")
            self.assertEqual(sorted(p.name for p in (v / f"lib/python{NOW}/site-packages").iterdir()), before)


class LoginTries(unittest.TestCase):
    """The login service restarts on failure, 2 minutes on: a pip that kept failing (a tested
    version gone from PyPI, no build) took the lock, wrote a log and ran pip 3 times every 2
    minutes, for good. Now only offline is tried again, and that at most HEAL_TRIES times or for a
    day; repair still tries, and the venv stays stale for check-system."""
    # (the service's run, as install.sh _heal does it, minus the lock and log)
    LOGIN = "any_venv_stale || exit 0; heal_venvs --login"

    def pip(self, why):
        return f'pip_pinned() {{ shift; echo "$*" >> "$HOME/pip.log"; PIP_PINNED_WHY={why}; return 1; }}; '

    def runs(self, home, v, why, n):
        """n runs of the login service; how many pip was asked."""
        for _ in range(n):
            sh(home, self.pip(why) + f"ft_venvs() {{ echo {v}; }}; heal_units() {{ :; }}; {self.LOGIN}")
        log = Path(home) / "pip.log"
        return len(log.read_text().splitlines()) if log.exists() else 0

    def test_a_version_gone_from_pypi_is_tried_once_at_login(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", compiled=True)
            self.assertEqual(self.runs(home, v, '"gone pkgx==1.0"', 5), 1)
            self.assertEqual(sh(home, f"venv_stale {v}").returncode, 0, "check-system must still warn")
            r = sh(home, self.pip("other") + f"ft_venvs() {{ echo {v}; }}; heal_units() {{ :; }}; heal_venvs")
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(len((Path(home) / "pip.log").read_text().splitlines()), 2)   # (repair still tries)
            ok = 'pip_pinned() { return 0; }; '
            self.assertEqual(sh(home, ok + f"ft_venvs() {{ echo {v}; }}; heal_units() {{ :; }}; heal_venvs").returncode, 0)
            self.assertNotEqual(sh(home, f"venv_stale {v}").returncode, 0)            # (a repair that got them)

    def test_offline_is_tried_again_a_bounded_number_of_times(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", compiled=True)
            tries = int(sh(home, "echo $HEAL_TRIES").stdout)
            self.assertEqual(self.runs(home, v, "offline", tries + 3), tries)
            r = sh(home, f"ft_venvs() {{ echo {v}; }}; any_venv_stale")
            self.assertNotEqual(r.returncode, 0, "the login service must stop")
            self.assertEqual(sh(home, f"venv_stale {v}").returncode, 0)

    def test_offline_for_over_a_day_stops_too(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", compiled=True)
            self.assertEqual(self.runs(home, v, "offline", 2), 2)
            pending = v / ".ft-heal-pending"
            first = [line for line in pending.read_text().splitlines() if line.startswith("#tries ")][0].split()
            self.assertEqual(first[1], "2")
            pending.write_text(pending.read_text().replace(f" {first[2]} ", f" {int(first[2]) - 86400} "))
            self.assertEqual(self.runs(home, v, "offline", 3), 2)       # (a day on: not tried again)

    def test_back_online_the_packages_come(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", compiled=True)
            self.runs(home, v, "offline", 2)
            ok = 'pip_pinned() { shift; echo "$*" >> "$HOME/ok.log"; return 0; }; '
            r = sh(home, ok + f"ft_venvs() {{ echo {v}; }}; heal_units() {{ :; }}; {self.LOGIN}")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((Path(home) / "ok.log").read_text().split(), ["pkgx"])   # (not the #tries note)
            self.assertFalse((v / ".ft-heal-pending").exists())

    def test_a_note_it_cant_read_ends_the_tries(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", NOW)
            (v / ".ft-heal-pending").write_text("pkgx\n#tries x$(touch boom) 1 offline\n")
            self.assertEqual(self.runs(home, v, "offline", 2), 0)
            self.assertFalse((Path(home) / "boom").exists())


class Lock(unittest.TestCase):
    def test_heal_waits_for_a_setup_of_the_same_venv(self):
        # (the window's ensure_qt_venv holding the venv, as when it opens during a login's heal:
        # the heal waits, then finds the venv current and leaves it)
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v")
            holder = subprocess.Popen(
                ["bash", "-c", f"source {ROOT}/lib/common.sh 2>/dev/null; venv_lock {v}; echo held; sleep 2; "
                               f"rm -rf {v}/lib/python3.0; mkdir -p {v}/lib/python{NOW}/site-packages; venv_unlock"],
                stdout=subprocess.PIPE, text=True, env={**os.environ, "HOME": home})
            self.assertEqual(holder.stdout.readline().strip(), "held")
            r = sh(home, Heal.PIP + f"heal_venv {v}; echo done")
            holder.wait()
            self.assertEqual(r.stdout.strip(), "done", r.stderr)
            self.assertFalse((Path(home) / "pip.log").exists())
            self.assertEqual(sorted(p.name for p in (v / "lib").iterdir()), [f"python{NOW}"])  # (left as the holder made it)


class Units(unittest.TestCase):
    def test_a_service_on_the_venv_is_started_again(self):
        with tempfile.TemporaryDirectory() as home:
            v = Path(home) / "v"
            tool = Path(home) / "tool"
            tool.write_text(f"#!{v}/bin/python\n")
            other = Path(home) / "other"
            other.write_text("#!/bin/bash\n")
            units = Path(home) / ".config/systemd/user"
            units.mkdir(parents=True)
            (units / "on-venv.service").write_text(f"[Service]\nExecStart={tool} --run\n[Install]\nWantedBy=default.target\n")
            (units / "not.service").write_text(f"[Service]\nExecStart={other}\n[Install]\nWantedBy=default.target\n")
            # (failed, enabled, wanted by an active default.target; every call logged)
            stub = ('sysctl_user() { echo "$*" >> "$HOME/calls"; case $1 in '
                    'is-active) [ "${@: -1}" = default.target ] ;; is-enabled) return 0 ;; '
                    'show) echo failed ;; esac; }; ')
            r = sh(home, stub + f"heal_units {v}")
            self.assertEqual(r.returncode, 0, r.stderr)
            calls = (Path(home) / "calls").read_text().splitlines()
            self.assertIn("reset-failed on-venv.service", calls)
            self.assertIn("start --no-block on-venv.service", calls)
            self.assertFalse([c for c in calls if "not.service" in c])

    def test_a_service_whose_bash_wrapper_execs_the_venv_program_too(self):
        # (Dictation's engine: `dictate --serve`, bash, execs dictate-parakeet on Parakeet's venv)
        with tempfile.TemporaryDirectory() as home:
            v = Path(home) / ".local/share/frame-tweaks/parakeet/venv"
            wrapper = Path(home) / "dictate"
            wrapper.write_text("#!/bin/bash\nexec dictate-parakeet --serve\n")
            units = Path(home) / ".config/systemd/user"
            units.mkdir(parents=True)
            (units / "frame-tweaks-dictate-engine.service").write_text(f"[Service]\nExecStart={wrapper} --serve\n")
            stub = ('sysctl_user() { echo "$*" >> "$HOME/calls"; case $1 in '
                    'is-active) [ "${@: -1}" = frame-tweaks-dictate-engine.service ] ;; esac; }; ')
            r = sh(home, stub + f"heal_units {v}")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("restart --no-block frame-tweaks-dictate-engine.service",
                          (Path(home) / "calls").read_text().splitlines())


class Unit(unittest.TestCase):
    def test_the_login_service_runs_heal(self):
        out = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), "unit", "heal", "/opt/ft"],
                             capture_output=True, text=True).stdout
        self.assertIn("ExecStart=/bin/bash /opt/ft/install.sh _heal\n", out)
        self.assertIn("WantedBy=default.target", out)
        self.assertIn("RestartMaxDelaySec=", out)                   # (tries further apart: LoginTries)


if __name__ == "__main__":
    unittest.main()
