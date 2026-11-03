"""Frame Tweaks' programs as systemd user units: run_unit / stop_units (lib/common.sh), the restart
policy of the services tweaks install, and lib/detached.sh, which runs the window's installs so
that closing the terminal doesn't cut them short. systemctl and systemd-run are stand-ins writing
what they were asked. Run: python3 -m unittest -v"""
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "gui"))
from helpers import sandbox_env, stub  # noqa: E402
import window_logic  # noqa: E402

# systemctl: the user manager answers unless NO_SYSTEMD is set; is-active says IS_ACTIVE (1: not
# running); list-units prints LIST; every call is logged.
SYSTEMCTL = r'''echo "systemctl $*" >> "$HOME/calls"
[ -z "${NO_SYSTEMD:-}" ] || exit 1
case " $* " in
    *" is-active "*) exit "${IS_ACTIVE:-1}" ;;
    *" list-units "*) printf '%b' "${LIST:-}" ;;
esac
exit 0'''
# systemd-run: its arguments, one per line, and the runtime folder it was given itself; with
# RUN_EXEC, it also runs the command after "--", as the unit would.
SYSTEMD_RUN = r'''printf '%s\n' "$@" > "$HOME/run-args"
echo "$XDG_RUNTIME_DIR" > "$HOME/run-runtime"
if [ -n "${RUN_EXEC:-}" ]; then
    while [ $# -gt 0 ] && [ "$1" != -- ]; do case $1 in --setenv=*) export "${1#--setenv=}" ;; esac; shift; done
    shift; "$@"
fi
exit "${RUN_STATUS:-0}"'''


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.stubs = self.home / "stubs"
        stub(self.stubs, "systemctl", SYSTEMCTL)
        stub(self.stubs, "systemd-run", SYSTEMD_RUN)

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, **extra):
        return sandbox_env(self.home, self.stubs, **extra)

    def sh(self, script, **extra):
        return subprocess.run(["bash", "-c", f"source {ROOT}/lib/common.sh 2>/dev/null; {script}"],
                              capture_output=True, text=True, env=self.env(**extra), timeout=30)

    def run_args(self):
        f = self.home / "run-args"
        return f.read_text().splitlines() if f.exists() else None

    def calls(self):
        f = self.home / "calls"
        return f.read_text().splitlines() if f.exists() else []


class RunUnit(Sandbox):
    def test_a_unit_with_limits_and_the_callers_session(self):
        r = self.sh('run_unit arrowpad desktop --memory 600M -- /bin/echo hi', DISPLAY=":2",
                    XDG_RUNTIME_DIR="/run/user/1000/nested_plasma", DBUS_SESSION_BUS_ADDRESS="unix:path=/tmp/dbus-x")
        self.assertEqual(r.returncode, 0, r.stderr)
        args = self.run_args()
        self.assertEqual(args[:4], ["--user", "--quiet", "--collect", "--unit=ft-arrowpad-desktop"])
        self.assertIn("--slice=app-ft.slice", args)       # (inside app.slice: VR memory guard's limit)
        for prop in ("MemoryMax=600M", "MemorySwapMax=256M", "TasksMax=128", "NoNewPrivileges=yes",
                     "KillMode=control-group", "IgnoreSIGPIPE=no"):
            self.assertEqual(args[args.index(prop) - 1], "-p", prop)
        # The program gets the caller's session (desktop mode's), systemd-run the user manager's bus.
        self.assertIn("--setenv=DISPLAY=:2", args)
        self.assertIn("--setenv=XDG_RUNTIME_DIR=/run/user/1000/nested_plasma", args)
        self.assertIn("--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/dbus-x", args)
        self.assertIn("UnsetEnvironment=WAYLAND_DISPLAY", args)       # (the caller has none)
        self.assertNotIn("UnsetEnvironment=DISPLAY", args)
        self.assertEqual((self.home / "run-runtime").read_text().strip(), f"/run/user/{os.getuid()}")
        self.assertEqual(args[args.index("--") + 1:], ["/bin/echo", "hi"])

    def test_default_memory(self):
        self.sh("run_unit snip shot -- /bin/true")
        self.assertIn("MemoryMax=800M", self.run_args())

    def test_running_already_starts_nothing(self):
        r = self.sh("run_unit arrowpad vr -- /bin/true || echo rc=$?", IS_ACTIVE="0")     # (common.sh: set -e)
        self.assertIn("rc=3", r.stdout)
        self.assertIsNone(self.run_args())

    def test_without_systemd_the_program_starts_as_before(self):
        mark = self.home / "started"
        r = self.sh(f"run_unit arrowpad desktop -- /bin/touch {mark}; echo rc=$?", NO_SYSTEMD="1")
        self.assertIn("rc=0", r.stdout)
        self.assertIsNone(self.run_args())
        for _ in range(50):                # (setsid -f: in the background)
            if mark.exists():
                break
            time.sleep(0.1)
        self.assertTrue(mark.exists())

    def test_names_that_stop_units_could_mistake_are_refused(self):
        for tweak, name in (("vr", "dashboard-x"), ("Vr", "x"), ("vr", ""), ("../x", "y")):
            r = self.sh(f"run_unit '{tweak}' '{name}' -- /bin/true; echo survived")
            self.assertNotIn("survived", r.stdout, (tweak, name))
            self.assertIsNone(self.run_args())


class StopUnits(Sandbox):
    LIST = (r"ft-vr-a.service loaded active running a\n"
            r"ft-vr-dashboard-b.service loaded active running b\n"
            r"\xe2\x97\x8f ft-vr-c.service loaded failed failed c\n")

    def test_only_the_tweaks_own(self):
        r = self.sh("stop_units vr; echo rc=$?", LIST=self.LIST)
        self.assertIn("rc=0", r.stdout)
        stops = [c for c in self.calls() if " stop " in f"{c} "]
        self.assertEqual(stops, ["systemctl --user stop ft-vr-a.service ft-vr-c.service"])

    def test_none(self):
        r = self.sh("stop_units arrowpad || echo rc=$?", LIST=self.LIST)
        self.assertIn("rc=1", r.stdout)
        self.assertFalse([c for c in self.calls() if " stop " in f"{c} "])

    def test_stop_processes_stops_units_first(self):
        text = (ROOT / "install.sh").read_text()
        body = text[text.index("stop_processes() {"):]
        body = body[:body.index("\n}\n")]
        self.assertIn('stop_units "$id" && n=1', body)     # (and then stopped.sh runs, as for a pattern)


class ArrowPadRun(Sandbox):
    """Arrow Pad's Run button: a unit of its own; running already, the pad itself (it tells the
    running one to hide or show)."""

    def run_sh(self, **extra):
        bin_ = self.home / ".local/bin"
        stub(bin_, "arrowpad", f'echo "$*" > {self.home}/pad')
        return subprocess.run(["bash", str(ROOT / "packs/core/arrowpad/run.sh")], capture_output=True, text=True,
                              env=self.env(FRAME_TWEAKS_LIB=str(ROOT / "lib"), **extra), timeout=30)

    def test_desktop(self):
        r = self.run_sh(DISPLAY=":2")
        self.assertEqual(r.returncode, 0, r.stderr)
        args = self.run_args()
        self.assertIn("--unit=ft-arrowpad-desktop", args)
        self.assertEqual(args[args.index("--") + 1:], [str(self.home / ".local/bin/arrowpad"), "--desktop"])

    def test_vr(self):
        self.run_sh(DISPLAY=":0")
        self.assertIn("--unit=ft-arrowpad-vr", self.run_args())

    def test_running_already(self):
        r = self.run_sh(DISPLAY=":2", IS_ACTIVE="0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(self.run_args())
        self.assertEqual((self.home / "pad").read_text().strip(), "--desktop")


class Detached(Sandbox):
    """lib/detached.sh: the window's installs as a service on a relayed pty, or plainly."""

    def detached(self, *cmd, **extra):
        return subprocess.run(["bash", str(ROOT / "lib/detached.sh"), *cmd], capture_output=True, text=True,
                              env=self.env(FRAME_TWEAKS_SPLASH="off", FRAME_TWEAKS_NO_TMUX="1", **extra), timeout=30)

    def test_as_a_service(self):
        r = self.detached("./install.sh", "update", "--to", "v1.2.3", FRAME_TWEAKS_DRY_RUN="1", DISPLAY=":2")
        self.assertEqual(r.returncode, 0, r.stderr)
        line = r.stdout.strip()
        self.assertTrue(line.startswith("would run: env XDG_RUNTIME_DIR="), line)
        self.assertRegex(line, r"systemd-run --user --pty --quiet --collect --unit=ft-install-\d+ ")
        self.assertIn("--working-directory=" + str(ROOT), line)
        self.assertIn("--setenv=FRAME_TWEAKS_SPLASH=off", line)      # (drawn outside: lib/splash.py)
        self.assertIn("--setenv=DISPLAY=:2", line)
        self.assertNotIn("NoNewPrivileges", line)                    # (installers use sudo)
        self.assertIn("trap", line)
        self.assertTrue(line.endswith("./install.sh update --to v1.2.3"), line)

    def test_runs_it_and_passes_its_exit_status_on(self):
        r = self.detached("./install.sh", "update", RUN_STATUS="3")
        self.assertEqual(r.returncode, 3, r.stderr)        # (the window's "updated, a tweak failed")
        args = self.run_args()
        self.assertIn("--pty", args)
        i = args.index("--")
        self.assertEqual(args[i + 1:i + 3], ["bash", "-c"])
        self.assertIn('trap "" HUP', args[i + 3])          # (the relay's hangup doesn't end it)
        self.assertEqual(args[-2:], ["./install.sh", "update"])

    def test_without_systemd_plainly(self):
        r = self.detached("./install.sh", "update", FRAME_TWEAKS_DRY_RUN="1", NO_SYSTEMD="1")
        self.assertEqual(r.stdout.strip(), "would run: ./install.sh update")
        r = self.detached("bash", "-c", "echo plain; exit 4", NO_SYSTEMD="1")
        self.assertEqual((r.returncode, r.stdout.strip()), (4, "plain"))
        self.assertIsNone(self.run_args())


# tmux: new-session runs its command at once (as the session would), attach-session prints ATTACHED,
# has-session answers HAS (1: gone); every call is logged.
TMUX = r'''echo "tmux $*" >> "$HOME/calls"
case " $* " in
    *" new-session "*) for a; do last=$a; [ "$a" = ";" ] && break; cmd=$a; done; bash -c "$cmd" ;;
    *" attach-session "*) echo ATTACHED ;;
    *" has-session "*) exit "${HAS:-1}" ;;
esac
exit 0'''


class DetachedTmux(Sandbox):
    """With tmux (SteamOS has it): the install runs in a tmux session the service owns, and the
    terminal attaches; closing it detaches, and ./install.sh attach brings it back."""
    def setUp(self):
        super().setUp()
        stub(self.stubs, "tmux", TMUX)

    def detached(self, *cmd, **extra):
        return subprocess.run(["bash", str(ROOT / "lib/detached.sh"), *cmd], capture_output=True, text=True,
                              env=self.env(FRAME_TWEAKS_SPLASH="off", **extra), timeout=30)

    def test_runs_in_tmux_and_passes_its_exit_status_on(self):
        r = self.detached("bash", "-c", "exit 3", RUN_EXEC="1")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        args = self.run_args()
        self.assertIn("Type=forking", args)
        i = args.index("--")
        self.assertEqual(args[i + 1:i + 3], ["tmux", "-L"])
        self.assertRegex(args[i + 3], r"^ft-install-\d+$")
        self.assertIn("status", args)                                 # (its status bar off)
        self.assertTrue(any("attach-session" in c for c in self.calls()))

    def test_the_splash_is_drawn_inside_the_session_and_its_replay_printed_after(self):
        """Around tmux's attach, the splash saw tmux take the alternate screen, handed it the whole
        terminal and only came back at the very end: so it runs inside the session, around the
        command, and what it prints again at the end (FRAME_TWEAKS_SPLASH_REPLAY) is printed
        here once the session is over (tmux's screen goes with it)."""
        r = self.detached("bash", "-c", 'printf "the output again" > "$FRAME_TWEAKS_SPLASH_REPLAY"', RUN_EXEC="1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        args = self.run_args()
        session = next(a for a in args if "lib/splash.py" in a)
        self.assertRegex(session, r"python3 lib/splash\.py -- bash -c ")
        self.assertIn("--setenv=FRAME_TWEAKS_SPLASH=off", args)          # (the caller's choice goes in)
        self.assertTrue(any(a.startswith("--setenv=FRAME_TWEAKS_SPLASH_REPLAY=") for a in args))
        self.assertTrue(r.stdout.endswith("the output again"), r.stdout)
        self.assertFalse(list(Path(self.tmp.name).rglob("ft-install-*.out")))   # (and removed)

    def test_detached_it_goes_on_and_says_so(self):
        r = self.detached("bash", "-c", "exit 0", HAS="0")             # (the session still there)
        self.assertEqual(r.returncode, 0)
        self.assertIn("./install.sh attach", r.stdout)

    def test_attach_finds_the_running_one(self):
        socks = Path(self.tmp.name) / "tmux-sockets"
        sockdir = socks / f"tmux-{os.getuid()}"
        sockdir.mkdir(parents=True)
        import socket
        s1 = socket.socket(socket.AF_UNIX)
        s1.bind(str(sockdir / "ft-install-42"))
        self.addCleanup(s1.close)
        r = subprocess.run([str(ROOT / "install.sh"), "attach"], capture_output=True, text=True, timeout=30,
                           env=self.env(TMUX_TMPDIR=str(socks), HAS="0"))
        self.assertIn("ATTACHED", r.stdout, r.stderr)
        self.assertIn("tmux -L ft-install-42 attach-session -t ft-install-42", self.calls())
        r = subprocess.run([str(ROOT / "install.sh"), "attach"], capture_output=True, text=True, timeout=30,
                           env=self.env(TMUX_TMPDIR=str(socks), HAS="1"))
        self.assertIn("No install is running", r.stdout)


class WindowSide(unittest.TestCase):
    def test_detached_command(self):
        self.assertEqual(window_logic.detached("./install.sh update --to v1"),
                         "bash lib/detached.sh ./install.sh update --to v1")

    def test_install_running_reads_the_kernels_locks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lock = tmp / "install.lock"
            lock.touch()
            ino = lock.stat().st_ino
            proc = tmp / "proc"
            (proc / "4242/fd").mkdir(parents=True)
            (proc / "4242/fd/8").symlink_to(lock)
            other = tmp / "other"
            other.touch()
            (proc / "77/fd").mkdir(parents=True)
            (proc / "77/fd/3").symlink_to(other)
            locks = proc / "locks"
            self.assertFalse(window_logic.install_running(lock, str(proc)))     # (no list: not running)
            locks.write_text(f"1: POSIX  ADVISORY  WRITE 99 00:1b:{ino} 0 EOF\n")
            self.assertFalse(window_logic.install_running(lock, str(proc)))
            locks.write_text(f"1: FLOCK  ADVISORY  WRITE 77 00:1b:{ino} 0 EOF\n")    # (same inode, another file)
            self.assertFalse(window_logic.install_running(lock, str(proc)))
            locks.write_text(f"1: FLOCK  ADVISORY  WRITE 4242 00:1b:{ino} 0 EOF\n"
                             f"1: -> FLOCK  ADVISORY  WRITE 77 00:1b:{ino} 0 EOF\n")
            self.assertTrue(window_logic.install_running(lock, str(proc)))
            locks.write_text(f"1: -> FLOCK  ADVISORY  WRITE 4242 00:1b:{ino} 0 EOF\n")   # (only waiting)
            self.assertFalse(window_logic.install_running(lock, str(proc)))

    def test_install_running_with_a_real_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "install.lock"
            lock.touch()
            p = subprocess.Popen(["flock", str(lock), "sleep", "30"])
            try:
                for _ in range(50):
                    if window_logic.install_running(lock):
                        break
                    time.sleep(0.1)
                self.assertTrue(window_logic.install_running(lock))
            finally:
                p.kill()
                p.wait()
            self.assertFalse(window_logic.install_running(lock))


class RestartPolicy(unittest.TestCase):
    """Every service a tweak installs that stays up restarts on a crash, after 1 s growing to 32 s,
    and gives up after 10 starts in 5 minutes; oneshots are left out."""
    WANT_SERVICE = {"Restart": "on-failure", "RestartSec": "1", "RestartSteps": "5", "RestartMaxDelaySec": "32"}
    WANT_UNIT = {"StartLimitIntervalSec": "300", "StartLimitBurst": "10"}

    @staticmethod
    def units():
        """(where, text) for every unit file in the packs and every unit an install script writes
        from a here-document."""
        for f in sorted(ROOT.glob("packs/*/*/*.service")):
            if "attic" not in f.parts:
                yield str(f.relative_to(ROOT)), f.read_text()
        for f in sorted(ROOT.glob("packs/*/*/*.sh")):
            if "attic" in f.parts:
                continue
            for m in re.finditer(r"<<'?(\w+)'?\n(.*?)\n\1\n", f.read_text(), re.S):
                if "[Service]" in m.group(2):
                    yield f"{f.relative_to(ROOT)} ({m.group(2).splitlines()[1]})", m.group(2)

    @staticmethod
    def sections(text):
        out, cur = {}, None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                cur = out.setdefault(line[1:-1], {})
            elif cur is not None and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                cur[k.strip()] = v.strip()
        return out

    def test_long_running_services(self):
        found = 0
        for where, text in self.units():
            s = self.sections(text)
            # (oneshots, and drop-ins for another unit, such as steamvr.service's: no ExecStart)
            if s.get("Service", {}).get("Type") == "oneshot" or "ExecStart" not in s.get("Service", {}):
                continue
            found += 1
            with self.subTest(where):
                self.assertEqual({k: s["Service"].get(k) for k in self.WANT_SERVICE}, self.WANT_SERVICE)
                self.assertEqual({k: s.get("Unit", {}).get(k) for k in self.WANT_UNIT}, self.WANT_UNIT)
        self.assertGreaterEqual(found, 7)       # (ydotoold, charge-limit, wallet's two, the dashboard, dictation's two)


if __name__ == "__main__":
    unittest.main()
