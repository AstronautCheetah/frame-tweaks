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

    def test_heal_venvs_leaves_a_current_venv(self):
        with tempfile.TemporaryDirectory() as home:
            v = old_venv(Path(home) / "v", NOW)
            before = sorted(p.name for p in (v / f"lib/python{NOW}/site-packages").iterdir())
            r = sh(home, self.PIP + f"ft_venvs() {{ echo {v}; }}; heal_venvs")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")
            self.assertEqual(sorted(p.name for p in (v / f"lib/python{NOW}/site-packages").iterdir()), before)


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


class Unit(unittest.TestCase):
    def test_the_login_service_runs_heal(self):
        out = subprocess.run([sys.executable, str(ROOT / "lib/installer.py"), "unit", "heal", "/opt/ft"],
                             capture_output=True, text=True).stdout
        self.assertIn("ExecStart=/bin/bash /opt/ft/install.sh _heal\n", out)
        self.assertIn("WantedBy=default.target", out)


if __name__ == "__main__":
    unittest.main()
