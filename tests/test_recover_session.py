"""Desktop & VR Recovery's recover-session (packs/core/tools): what it reads to bring a VR session
back after the session's D-Bus went down (SteamOS 0.5.7's beta, VLC). Run: python3 -m unittest -v"""
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(script, stdin="", **env):
    with tempfile.TemporaryDirectory() as home:
        return subprocess.run(["bash", "-c", f"source {ROOT}/packs/core/tools/recover-session 2>/dev/null; {script}"],
                              input=stdin, capture_output=True, text=True,
                              env={**os.environ, "HOME": home, **env})


# `pactl list cards` as PipeWire printed it on the Frame: the headphones on calls only (after the
# crash), and a speaker with A2DP as well.
CARDS = """Card #61
\tName: bluez_card.AC_BF_71_03_97_6F
\tDriver: module-bluez5-device.c
\tProfiles:
\t\toff: Off (sinks: 0, sources: 0, priority: 0, available: yes)
\t\theadset-head-unit-cvsd: Headset Head Unit (HSP/HFP, codec CVSD) (sinks: 1, sources: 1, priority: 2, available: yes)
\t\theadset-head-unit: Headset Head Unit (HSP/HFP, codec MSBC) (sinks: 1, sources: 1, priority: 3, available: yes)
\tActive Profile: headset-head-unit
Card #62
\tName: bluez_card.F4_4E_FD_95_22_ED
\tProfiles:
\t\ta2dp-sink: High Fidelity Playback (A2DP Sink, codec AAC) (sinks: 1, sources: 0, priority: 133, available: yes)
\t\theadset-head-unit: Headset Head Unit (HSP/HFP, codec MSBC) (sinks: 1, sources: 1, priority: 6, available: yes)
\tActive Profile: a2dp-sink
Card #63
\tName: alsa_card.platform-sound
\tProfiles:
\t\tHiFi: Default (sinks: 2, sources: 2, priority: 8000, available: yes)
"""


class CallOnly(unittest.TestCase):
    def test_only_the_card_without_a2dp(self):
        self.assertEqual(sh("call_only_devices", CARDS).stdout.split(), ["AC:BF:71:03:97:6F"])

    def test_none_when_all_play_a2dp(self):
        self.assertEqual(sh("call_only_devices", CARDS.split("Card #62")[1]).stdout.strip(), "")


class SessionVars(unittest.TestCase):
    def proc(self, root, pid, env):
        (root / str(pid)).mkdir(parents=True)
        (root / str(pid) / "environ").write_bytes(b"\0".join(e.encode() for e in env) + b"\0")

    def test_the_session_variables_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.proc(root, 7, ["HOME=/var/empty", "DISPLAY=:0", "GAMESCOPE_WAYLAND_DISPLAY=gamescope-0",
                                "STEAM_GAME_DISPLAY_0=:1", "XDG_CURRENT_DESKTOP=gamescope", "PATH=/usr/bin",
                                "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS=0", "XCURSOR_THEME=steam"])
            out = sh("session_vars_of 7", FRAME_TWEAKS_PROC=d).stdout.split()
            self.assertEqual(sorted(out), sorted(["DISPLAY=:0", "GAMESCOPE_WAYLAND_DISPLAY=gamescope-0",
                                                  "STEAM_GAME_DISPLAY_0=:1", "XDG_CURRENT_DESKTOP=gamescope",
                                                  "SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS=0", "XCURSOR_THEME=steam"]))

    def test_nothing_from_a_process_without_a_display(self):
        # (a Steam started after the cleanup: what it has is no use)
        with tempfile.TemporaryDirectory() as d:
            self.proc(Path(d), 8, ["XDG_SESSION_TYPE=tty", "STEAM_USE_MANGOAPP=1"])
            r = sh("session_vars_of 8", FRAME_TWEAKS_PROC=d)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip(), "")


def x_sockets(d, *names):
    socks = []
    for name in names:
        s = socket.socket(socket.AF_UNIX)
        s.bind(str(Path(d) / name))
        socks.append(s)
    return socks


class FirstDisplay(unittest.TestCase):
    def test_the_lowest_x_socket(self):
        with tempfile.TemporaryDirectory() as d:
            socks = x_sockets(d, "X1", "X0", "X10")
            (Path(d) / "X5").write_text("")             # (not a socket)
            self.assertEqual(sh("first_display", FRAME_TWEAKS_X11=d).stdout.strip(), ":0")
            for s in socks:
                s.close()

    def test_none_without_a_socket(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertNotEqual(sh("first_display", FRAME_TWEAKS_X11=d).returncode, 0)


# (the user manager stubbed: show-environment prints $ENV_NOW, every other call is logged)
MANAGER = ('sysctl_user() { case $1 in show-environment) printf "%b" "$ENV_NOW" ;; '
           'show) echo 0 ;; is-active) return 1 ;; *) echo "$*" >> "$HOME/calls" ;; esac; }; '
           'calls() { cat "$HOME/calls" 2>/dev/null; }; ')


class Restore(unittest.TestCase):
    def test_display_alone_when_no_program_has_it(self):
        # (after a SteamVR restart: its new server lacks DISPLAY like everything else since the crash,
        # while start-gamescope-session removed DISPLAY only)
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as proc:
            socks = x_sockets(d, "X0", "X1")
            r = sh(MANAGER + "session_source() { return 1; }; restore_display && calls",
                   ENV_NOW="GAMESCOPE_WAYLAND_DISPLAY=gamescope-0\\n", FRAME_TWEAKS_X11=d, FRAME_TWEAKS_PROC=proc)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("set-environment DISPLAY=:0", r.stdout)
            for s in socks:
                s.close()

    def test_nothing_outside_a_gamescope_session(self):
        with tempfile.TemporaryDirectory() as d:
            socks = x_sockets(d, "X0")
            r = sh(MANAGER + "session_source() { return 1; }; restore_display; echo rc=$?; calls",
                   ENV_NOW="", FRAME_TWEAKS_X11=d)
            self.assertIn("rc=1", r.stdout)
            self.assertNotIn("set-environment", r.stdout)
            for s in socks:
                s.close()


class WaitForSteam(unittest.TestCase):
    def test_steam_is_not_restarted_while_the_display_cannot_be_put_back(self):
        # (the first fix restarted Steam every few seconds for three minutes, each copy failing)
        r = sh(MANAGER + "restore_display() { return 1; }; steam_up() { return 1; }; wait_for_steam; calls",
               RECOVER_WAIT="0", ENV_NOW="")
        self.assertIn("Steam still doesn't stay up", r.stderr)    # (it waited, and gave up)
        self.assertNotIn("restart", r.stdout)
        self.assertNotIn("start --no-block", r.stdout)


class Usage(unittest.TestCase):
    def test_an_unknown_option_is_refused(self):
        self.assertEqual(sh("main --bogus").returncode, 2)


if __name__ == "__main__":
    unittest.main()
