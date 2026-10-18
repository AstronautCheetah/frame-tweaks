"""Shell helpers in lib/common.sh. Run: python3 -m unittest -v"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import kde_saves, sandbox_env, stub  # noqa: E402


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

    def test_your_edits_stay_when_it_is_written_again(self):
        """A rename or new icon from KDE's menu editor stays when the tweak's next update writes
        its entry again; the update's own changes come through. Its uninstall takes the copy kept."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            stubs, home = d / "stubs", d / "home"
            for name in ("systemctl", "update-desktop-database"):
                stub(stubs, name, "exit 0")
            desktop = d / "thing.desktop"
            desktop.write_text("[Desktop Entry]\nType=Application\nName=Thing\nComment=Does a thing\n"
                               "Exec=@BIN@/thing %U\nIcon=thing\n")

            def run(command):
                r = subprocess.run(["bash", "-c", f'source {ROOT}/lib/common.sh; {command}'], capture_output=True,
                                   text=True, timeout=60, env=sandbox_env(home, stubs))
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            run(f'install_desktop "{desktop}"')
            menu = home / ".local/share/applications/thing.desktop"
            menu.write_text(kde_saves(menu.read_text(), Name="My thing", Icon="star"))
            desktop.write_text(desktop.read_text().replace("Does a thing", "Does it better").replace(" %U", " --new %U"))
            run(f'install_desktop "{desktop}"')
            lines = menu.read_text().splitlines()
            for line in ("Name=My thing", "Icon=star", "Comment=Does it better", f"Exec={home}/.local/bin/thing --new %U"):
                self.assertIn(line, lines)
            self.assertEqual(lines[0], "[Desktop Entry]")
            run("remove_desktop thing.desktop")
            self.assertFalse(menu.exists())
            self.assertFalse((home / ".local/share/frame-tweaks/menu-built/thing.desktop").exists())
            run(f'install_desktop "{desktop}"; remove_files "$APPS/thing.desktop"')    # (a pack's own way)
            self.assertFalse((home / ".local/share/frame-tweaks/menu-built/thing.desktop").exists())


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



@unittest.skipUnless(shutil.which("ldd") and shutil.which("true"), "needs ldd")
class RunsHere(unittest.TestCase):
    """runs_here: a program the system can load passes; one needing a library that isn't there,
    or one ldd can't load at all (a build for another architecture, which ldd calls "not a
    dynamic executable"), doesn't, saying why. (It took the second for one that runs: then an
    Arch Linux ARM build for the wrong machine replaced a working ydotool.)"""

    def runs_here(self, program):
        r = subprocess.run(["bash", "-c", f'source {ROOT}/lib/common.sh 2>/dev/null; runs_here "{program}"'],
                           capture_output=True, text=True, timeout=60,
                           env=sandbox_env(self.home))
        return r.returncode, r.stdout.strip()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.real = Path(shutil.which("true")).resolve().read_bytes()

    def program(self, name, data):
        f = Path(self.tmp.name) / name
        f.write_bytes(data)
        f.chmod(0o755)
        return f

    def test_one_that_loads(self):
        self.assertEqual(self.runs_here(self.program("ok", self.real)), (0, ""))

    def test_one_for_another_machine(self):
        arm = bytearray(self.real)
        arm[4] = 1                                    # (ELF class: 32-bit)
        arm[18:20] = (40).to_bytes(2, "little")       # (machine: ARM, as armv7h builds are)
        rc, said = self.runs_here(self.program("arm32", arm))
        self.assertEqual(rc, 1)
        self.assertIn("not a dynamic executable", said)

    def test_one_needing_a_missing_library(self):
        lib = next(n for n in (b"libc.so.6", b"libc.so") if n + b"\0" in self.real)
        missing = self.real.replace(lib + b"\0", b"libq" + lib[4:] + b"\0", 1)
        rc, said = self.runs_here(self.program("missing", missing))
        self.assertEqual(rc, 1)
        self.assertIn("libq" + lib[4:].decode() + " => not found", said)

    def test_not_a_program_at_all(self):
        self.assertEqual(self.runs_here(self.program("script", b"#!/bin/sh\nexit 0\n"))[0], 1)


class PipPinned(unittest.TestCase):
    """pip_pinned, with a stand-in pip (its messages are pip 26's): the tested versions, tried a
    second time if that fails. Then only a tested version the package needs (pip's resolver says
    what it needs) that PyPI has no build of for this Python (pip, asked for that version alone,
    lists others or names the Python it needs) is replaced, by the newest that has one; the other
    tested versions stay. Not if PyPI no longer has that version at all (deleted, as a hijacked
    account could, to have its own newer one taken), nor if PyPI can't say. A lost connection,
    the first time and the second, stops it, saying PyPI couldn't be reached; so does any other
    failure. (Any failure dropped every pin, with a warning that blamed the Python version.)"""
    # pip stand-in: logs "<kind> <arguments>" (pinned: -c, the tested versions; resolve: --report,
    # writing a report of $PIP_NEEDS; check: --dry-run; fallback: -c another file, kept as
    # $PIP_CALLS.cons; newest: no -c), then answers from $PIP_SAYS/<kind>.<n> (its nth call),
    # <kind>.<its last argument> or <kind>: the exit code on the first line, what it prints on
    # stderr after it. No file: exit 0.
    PIP = r'''kind=newest prev=
for a; do
    [ "$prev" = -c ] && { kind=fallback; [ "$a" = "$PIP_CONS" ] && kind=pinned || cp "$a" "$PIP_CALLS.cons"; }
    [ "$prev" = --report ] && printf '{"version": "1", "install": [%s]}' \
        "$(printf '{"metadata": {"name": "%s"}}\n' $PIP_NEEDS | paste -sd, -)" > "$a"
    prev=$a
done
case " $* " in *" --report "*) kind=resolve ;; *" --dry-run "*) kind=check ;; esac
n=$(grep -c "^$kind " "$PIP_CALLS" 2>/dev/null)
echo "$kind $*" >> "$PIP_CALLS"
f="$PIP_SAYS/$kind.$((n + 1))"; [ -f "$f" ] || f="$PIP_SAYS/$kind.${*: -1}"; [ -f "$f" ] || f="$PIP_SAYS/$kind"
[ -f "$f" ] || exit 0
tail -n +2 "$f" >&2
exit "$(head -1 "$f")"'''
    # PyPI's JSON for a release, through curl: the HTTP code from $CURL_SAYS/<name>, else 200
    # (000: no connection)
    CURL = r'''echo "$*" >> "$CURL_CALLS"
url=${*: -1}; name=${url#https://pypi.org/pypi/}; name=${name%%/*}
code=$(cat "$CURL_SAYS/$name" 2>/dev/null || echo 200)
printf %s "$code"; [ "$code" != 000 ] || exit 7'''
    CONS = ROOT / "lib/python-constraints.txt"
    PINS = dict(line.split("==") for line in CONS.read_text().splitlines() if "==" in line and line[0] != "#")
    QT = ("PyQt6", "PyQt6-Qt6", "pyqt6-sip")       # (what PyQt6 needs, as a report spells them)
    OFFLINE = ("WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after "
               "connection broken by 'NewConnectionError(\"HTTPSConnection(host='pypi.org', port=443): Failed to "
               "establish a new connection: [Errno 101] Network is unreachable\")': /simple/pyqt6/\n")
    CONFLICT = ("ERROR: Cannot install PyQt6 because these package versions have conflicting dependencies.\n"
                "ERROR: ResolutionImpossible: for help visit "
                "https://pip.pypa.io/en/latest/topics/dependency-resolution/#dealing-with-dependency-conflicts")
    DISK_FULL = "ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device"

    @classmethod
    def not_here(cls, name):
        return (f"ERROR: Could not find a version that satisfies the requirement {name}=={cls.PINS[name]} (from "
                f"versions: 13.14.0, 13.15.0)\nERROR: No matching distribution found for {name}=={cls.PINS[name]}")

    @classmethod
    def other_python(cls, name):
        return (f"ERROR: Ignored the following versions that require a different python version: {cls.PINS[name]} "
                f"Requires-Python >=3.16\nERROR: Could not find a version that satisfies the requirement "
                f"{name}=={cls.PINS[name]} (from versions: none)\nERROR: No matching distribution found for "
                f"{name}=={cls.PINS[name]}")

    @classmethod
    def gone(cls, name):
        return (f"ERROR: Could not find a version that satisfies the requirement {name}=={cls.PINS[name]} (from "
                f"versions: none)\nERROR: No matching distribution found for {name}=={cls.PINS[name]}")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.venv, self.says, self.calls = self.d / "venv", self.d / "says", self.d / "calls"
        self.pypi, self.curl_calls = self.d / "pypi", self.d / "curl-calls"
        self.says.mkdir()
        self.pypi.mkdir()
        (self.d / "home").mkdir()
        stub(self.venv / "bin", "pip", self.PIP)
        stub(self.venv / "bin", "python", f'[ "$1" = -V ] && {{ echo "Python 3.15.0"; exit 0; }}\nexec "{sys.executable}" "$@"')
        stub(self.d / "stubs", "curl", self.CURL)

    def install(self, package="PyQt6", needs=QT, checks=(), pypi=(), **says):
        """pip_pinned <package>, pip answering as says has it ({"pinned_2": (0, "")}: its second
        pinned call) and, asked about one tested version alone, as checks has it ({"PyQt6_sip":
        ...}); its resolver finding the package needs `needs`; PyPI's JSON answering as pypi has
        it ({"pyqt6-sip": 404}). (exit code, what it printed on stderr, its pip calls' kinds)."""
        for name, (rc, text) in [*says.items(), *((f"check_{p}=={self.PINS[p]}", a) for p, a in dict(checks).items())]:
            (self.says / name.replace("_", ".", 1)).write_text(f"{rc}\n{text}\n")
        for name, code in dict(pypi).items():
            (self.pypi / name).write_text(f"{code}\n")
        r = subprocess.run(["bash", "-c", f'source {ROOT}/lib/common.sh; pip_pinned "{self.venv}" {package}'],
                           capture_output=True, text=True, timeout=60,
                           env=sandbox_env(self.d / "home", self.d / "stubs", PIP_CALLS=self.calls, PIP_SAYS=self.says,
                                           PIP_CONS=self.CONS, PIP_NEEDS=" ".join(needs), CURL_SAYS=self.pypi,
                                           CURL_CALLS=self.curl_calls))
        calls = self.calls.read_text().splitlines() if self.calls.exists() else []
        # (off the Frame, CI's x86_64 say, common.sh warns about the processor as it's sourced:
        # not pip_pinned's to answer for, so left out)
        said = "".join(l for l in r.stderr.splitlines(True) if "target the Steam Frame (aarch64)" not in l)
        return r.returncode, said, [c.split(" ", 1)[0] for c in calls]

    def call(self, kind):
        return [c for c in self.calls.read_text().splitlines() if c.startswith(kind + " ")]

    def test_the_tested_versions(self):
        rc, said, calls = self.install()
        self.assertEqual((rc, calls), (0, ["pinned"]), said)
        self.assertIn(f"-q -c {self.CONS} PyQt6", self.calls.read_text())
        self.assertNotIn("warning", said)

    def test_a_dropped_connection_is_tried_again(self):
        rc, said, calls = self.install(pinned_1=(1, self.OFFLINE + self.CONFLICT), pinned_2=(0, ""))
        self.assertEqual((rc, calls), (0, ["pinned", "pinned"]), said)

    def test_no_connection_keeps_the_pins(self):
        rc, said, calls = self.install(pinned=(1, self.OFFLINE + self.CONFLICT))
        self.assertNotEqual(rc, 0)
        self.assertEqual(calls, ["pinned", "pinned"])
        self.assertIn("Couldn't reach PyPI to install PyQt6: check the Internet connection, then try again.", said)

    def test_no_build_of_a_tested_version_here_takes_the_newest_of_that_one(self):
        rc, said, calls = self.install(pinned=(1, self.CONFLICT), checks={"PyQt6_sip": (1, self.not_here("PyQt6_sip"))})
        self.assertEqual((rc, calls), (0, ["pinned", "pinned", "resolve", "check", "check", "check", "fallback"]), said)
        self.assertIn("install -q --dry-run --ignore-installed --only-binary :all: --report ", self.call("resolve")[0])
        self.assertEqual([c.rsplit(" ", 1)[1] for c in self.call("check")],          # (only what PyQt6 needs)
                         [f"{p}=={self.PINS[p]}" for p in ("PyQt6", "PyQt6-Qt6", "PyQt6_sip")])
        self.assertIn("install -q --dry-run --no-deps --only-binary :all: ", self.call("check")[0])
        sip = f"PyQt6_sip=={self.PINS['PyQt6_sip']}"
        self.assertIn(f"PyPI has no build of {sip} for this Python (Python 3.15.0) and system; installing the newest "
                      "PyQt6_sip that has one instead. The other tested versions stay.", said)
        self.assertRegex(self.call("fallback")[0], r"^fallback install -q -c \S+ PyQt6$")
        kept = Path(f"{self.calls}.cons").read_text().splitlines()
        self.assertNotIn(sip, kept)
        self.assertEqual(kept, [line for line in self.CONS.read_text().splitlines() if line != sip])
        [ask] = self.curl_calls.read_text().splitlines()                           # (it's still on PyPI)
        self.assertTrue(ask.startswith("--proto =https --proto-redir =https "), ask)
        self.assertTrue(ask.endswith(f" https://pypi.org/pypi/pyqt6-sip/{self.PINS['PyQt6_sip']}/json"), ask)

    def test_one_needing_another_python_takes_the_newest_of_that_one(self):
        rc, said, calls = self.install(pinned=(1, self.CONFLICT), checks={"PyQt6": (1, self.other_python("PyQt6"))})
        self.assertEqual((rc, calls[-1]), (0, "fallback"), said)
        self.assertIn(f"PyPI has no build of PyQt6=={self.PINS['PyQt6']} for this Python", said)
        self.assertNotIn(f"PyQt6=={self.PINS['PyQt6']}", Path(f"{self.calls}.cons").read_text().splitlines())

    def test_a_tested_version_deleted_from_pypi_stops_it(self):
        """A hijacked account deletes the tested release and uploads a newer one: pip lists the
        others, as for a missing build, but PyPI no longer has that release at all."""
        rc, said, calls = self.install(pinned=(1, self.CONFLICT), checks={"PyQt6_sip": (1, self.not_here("PyQt6_sip"))},
                                       pypi={"pyqt6-sip": 404})
        self.assertNotEqual(rc, 0)
        self.assertNotIn("fallback", calls)
        self.assertIn(f"PyQt6_sip=={self.PINS['PyQt6_sip']}, the tested version, is no longer on PyPI, so PyQt6 isn't "
                      "installed: a deleted release isn't replaced by another one. Please report this.", said)

    def test_when_pypi_cant_say_whether_it_has_it(self):
        for code in ("000", "503"):
            with self.subTest(code=code):
                self.calls.unlink(missing_ok=True)
                rc, said, calls = self.install(pinned=(1, self.CONFLICT),
                                               checks={"PyQt6_sip": (1, self.not_here("PyQt6_sip"))},
                                               pypi={"pyqt6-sip": code})
                self.assertNotEqual(rc, 0)
                self.assertNotIn("fallback", calls)
                self.assertIn("Couldn't reach PyPI to install PyQt6", said)

    def test_a_tested_version_it_doesnt_need_changes_nothing(self):
        """jeepney fails on a full disk, while the tested PyQt6_sip has no build here: jeepney
        doesn't need it, so that's no reason to install another jeepney."""
        rc, said, calls = self.install("jeepney", needs=("jeepney",), pinned=(1, self.DISK_FULL),
                                       checks={"PyQt6_sip": (1, self.not_here("PyQt6_sip"))})
        self.assertNotEqual(rc, 0)
        self.assertEqual(calls, ["pinned", "pinned", "resolve", "check"])
        self.assertEqual(self.call("check")[0].rsplit(" ", 1)[1], f"jeepney=={self.PINS['jeepney']}")
        self.assertIn("Couldn't install jeepney (see above).", said)

    def test_any_other_failure_keeps_the_pins(self):
        for case, answers, kinds in (
                ("each version there", {}, ["resolve", "check", "check", "check"]),
                ("that one gone altogether", {"checks": {"PyQt6": (1, self.gone("PyQt6"))}}, ["resolve", "check"]),
                ("not even the newest installs", {"resolve": (1, self.gone("PyQt6"))}, ["resolve"])):
            with self.subTest(case):
                self.calls.unlink(missing_ok=True)
                rc, said, calls = self.install(pinned=(1, self.DISK_FULL), **answers)
                self.assertNotEqual(rc, 0)
                self.assertEqual(calls, ["pinned", "pinned", *kinds])
                self.assertIn("No space left on device", said)               # (pip's own words, shown)
                self.assertIn("Couldn't install PyQt6 (see above).", said)

    def test_no_connection_for_the_checks_either(self):
        for answers in ({"resolve": (1, self.OFFLINE + self.gone("PyQt6"))},
                        {"checks": {"PyQt6": (1, self.OFFLINE + self.gone("PyQt6"))}}):
            with self.subTest(answers):
                self.calls.unlink(missing_ok=True)
                rc, said, calls = self.install(pinned=(1, self.CONFLICT), **answers)
                self.assertNotEqual(rc, 0)
                self.assertNotIn("fallback", calls)
                self.assertIn("Couldn't reach PyPI", said)


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
