"""Desktop & VR Recovery's recover-session (packs/core/tools): what it reads to bring a VR session
back after the session's D-Bus went down (SteamOS 0.5.7's beta, VLC). Run: python3 -m unittest -v"""
import os
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


class Usage(unittest.TestCase):
    def test_an_unknown_option_is_refused(self):
        self.assertEqual(sh("main --bogus").returncode, 2)


if __name__ == "__main__":
    unittest.main()
