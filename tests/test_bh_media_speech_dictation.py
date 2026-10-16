"""The Speech engine's installer and Dictation's toggle, in a throwaway home with stand-ins for
the tools that would download, record, play or notify. A speech.conf without a language (only
the engine chosen, or reset) is English (US): nothing to download, a real language for
speech-dispatcher. Without speech-dispatcher (SteamOS 0.5.6 removed it) Speech still installs, for
Narrate, and an earlier speech-dispatcher setup is undone. A recording that ended by itself is
transcribed (by the next press, or the auto-stop), not "auto-stopped" into a new one. Installing
removes the models older versions downloaded, unless the settings use one. Every setting the
README lists is in the example settings file."""
import sys
import os
import re
import shlex
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
import xkb  # noqa: E402  (lib/, put on sys.path by helpers)
SPEECH = ROOT / "packs/core/speech"
DICTATION = ROOT / "packs/core/dictation"


def xkb_compiles():
    try:
        xkb.Keymap("fr")
        return True
    except OSError:
        return False


def pin(path, key):
    return next(l.split("=", 1)[1] for l in path.read_text().splitlines() if l.startswith(key + "="))


class Home(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "home"
        self.log = self.tmp / "log"
        self.log.write_text("")

    def stub(self, folder, name, body):
        stub(folder, name, body)


class SpeechLanguage(Home):
    def speechd(self, present=True):
        """A stand-in for SteamOS's speech-dispatcher (its settings and espeak-ng module), or none."""
        root = Path(tempfile.mkdtemp(dir=self.tmp))
        if present:
            (root / "etc/speech-dispatcher/modules").mkdir(parents=True)
            (root / "etc/speech-dispatcher/speechd.conf").write_text(
                'Include "clients/*.conf"\nAddModule "espeak-ng" "sd_espeak-ng" "espeak-ng.conf"\n'
                "DefaultModule espeak-ng\n")
            (root / "etc/speech-dispatcher/modules/espeak-ng.conf").write_text("")
            self.stub(root / "usr/lib/speech-dispatcher/speech-dispatcher-modules", "sd_espeak-ng", "exit 0")
        return root

    def install(self, conf, speechd=None, home=None):
        self.home = home or Path(tempfile.mkdtemp(dir=self.tmp))
        self.log.write_text("")
        d = self.home / ".local/share/frame-tweaks/speech"
        # Installed already: Piper at the pinned version and the English (US) voice
        self.stub(d / "piper", "piper", "exit 0")
        (d / "piper/.version").write_text(pin(SPEECH / "pin", "version") + "\n")
        for f in ("voice.onnx", "voice.onnx.json"):
            (d / f).write_text("")
        (d / "voice.version").write_text(pin(SPEECH / "voice.pin", "version") + "\n")
        (self.home / ".config/frame-tweaks").mkdir(parents=True, exist_ok=True)
        (self.home / ".config/frame-tweaks/speech.conf").write_text(conf)
        stubs = self.tmp / "stubs"     # no network; and never the real speech-dispatcher
        self.stub(stubs, "curl", f'echo "curl $*" >> {self.log}; exit 7')
        self.stub(stubs, "pkill", f'echo "pkill $*" >> {self.log}')
        env = sandbox_env(self.home, stubs, FRAME_TWEAKS_SPEECHD_ROOT=speechd or self.speechd())
        r = subprocess.run(["bash", str(SPEECH / "install.sh")], env=env, capture_output=True, text=True, timeout=60)
        return r, d

    def status(self, speechd):
        env = sandbox_env(self.home, FRAME_TWEAKS_SPEECHD_ROOT=speechd)
        return subprocess.run(["bash", str(SPEECH / "status.sh")], env=env, capture_output=True, text=True, timeout=30)

    def test_no_language_set_is_english_us(self):
        for conf, engine in (("SPEECH_ENGINE=espeak-ng\n", "espeak-ng"), ("", "piper")):   # engine chosen; reset
            with self.subTest(conf=conf):
                r, d = self.install(conf)
                self.assertNotIn("curl", self.log.read_text(), r.stdout + r.stderr)    # the voice it has
                narrate = (d / "narrate.conf").read_text()
                self.assertIn(f"engine={engine}\n", narrate)
                self.assertIn("language=en_US\n", narrate)
                self.assertIn("espeak_voice=en-us\n", narrate)
                self.assertEqual(r.returncode, 0, r.stderr)
                sd = (self.home / ".config/speech-dispatcher/speechd.conf").read_text()
                self.assertIn('DefaultLanguage "en"', sd)
                self.assertIn("speech-dispatcher apps use eSpeak NG", r.stdout)

    def test_without_speech_dispatcher_narrate_still_gets_its_voice(self):
        r, d = self.install("", speechd=self.speechd(present=False))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("engine=piper\n", (d / "narrate.conf").read_text())
        self.assertFalse((self.home / ".config/speech-dispatcher").exists())
        self.assertFalse((d / "sd_espeak-ng").exists())
        self.assertIn("Narrate uses Piper", r.stdout)
        self.assertNotIn("speech-dispatcher apps", r.stdout)
        s = self.status(self.speechd(present=False))
        self.assertEqual(s.returncode, 0, s.stdout + s.stderr)
        self.assertNotIn("speech-dispatcher uses", s.stdout)

    def test_an_earlier_setup_is_undone_once_speech_dispatcher_is_gone(self):
        """Installed while SteamOS had speech-dispatcher, then SteamOS removed it: installing
        again (an update, or Apply) takes Frame Tweaks' setup back out of ~/.config."""
        r, d = self.install("")
        self.assertEqual(r.returncode, 0, r.stderr)
        sd = self.home / ".config/speech-dispatcher/speechd.conf"
        self.assertTrue(sd.is_file())
        self.assertIn("speech-dispatcher uses espeak-ng", self.status(self.speechd()).stdout)
        r, d = self.install("", speechd=self.speechd(present=False), home=self.home)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(sd.exists())
        self.assertFalse((d / "sd_espeak-ng").exists())


class DictateAutoStop(Home):
    def dictate(self, max_seconds):
        """A copy of dictate with its runtime folder in the throwaway home, and stand-ins first on
        its PATH: nothing real records, plays, notifies, transcribes, copies or types. pw-record
        writes its file and ends at once, by itself (the microphone gone, say)."""
        self.run = self.tmp / "run"
        src = (DICTATION / "dictate").read_text()
        self.assertIn("RUN=/run/user/$(id -u)\n", src)
        script = self.tmp / "dictate"
        script.write_text(src.replace("RUN=/run/user/$(id -u)\n", f"RUN={self.run}\n"))     # (not the real one)
        script.chmod(0o755)
        bin_ = self.home / ".local/bin"           # first on dictate's PATH
        for name, body in (("pw-record", f'echo "record $*" >> {self.log}; for f; do :; done; echo RIFF > "$f"'),
                           ("pw-play", "exit 0"), ("notify-send", f'echo "notify $*" >> {self.log}'),
                           ("ffprobe", "echo 2.0"), ("ffmpeg", 'echo "[volumedetect] max_volume: -12.0 dB" >&2'),
                           ("whisper-cli", f'echo "whisper $*" >> {self.log}; echo "Hello from the recording."'),
                           ("wl-copy", f'echo "copy $(cat)" >> {self.log}'), ("ydotool", f'echo "ydotool $*" >> {self.log}')):
            self.stub(bin_, name, body)
        (self.home / ".config/frame-tweaks").mkdir(parents=True)
        (self.home / ".config/frame-tweaks/dictate.conf").write_text(f"DICTATE_MAX_SECONDS={max_seconds}\n")
        env = sandbox_env(self.home)
        return lambda *args: subprocess.run(["bash", str(script), *args], env=env, capture_output=True, text=True,
                                            timeout=30)

    def typed(self, seconds=5):
        end = time.monotonic() + seconds
        while "ydotool type" not in self.log.read_text() and time.monotonic() < end:
            time.sleep(0.05)
        return [l for l in self.log.read_text().splitlines() if l.startswith("ydotool type")]

    def test_a_recording_that_ended_by_itself_is_transcribed_not_restarted(self):
        """pw-record ended on its own. The auto-stop timer must not run the toggle into a new
        recording (it once did): it transcribes what was recorded, as it does a recording still
        running."""
        dictate = self.dictate(1)
        r = dictate()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.typed(), ["ydotool type --key-delay 2 -- Hello from the recording. "])
        log = self.log.read_text()
        self.assertEqual(log.count("record "), 1, log)
        self.assertEqual(dictate("--status").stdout.strip(), "idle")

    def test_the_next_press_transcribes_a_recording_that_ended_by_itself(self):
        """Pressed again after pw-record ended by itself: that recording is transcribed (its file
        kept as last.wav), as when it's still running. It started a new recording instead, the
        last one's file left behind."""
        dictate = self.dictate(2)
        self.assertEqual(dictate().returncode, 0)
        time.sleep(0.8)                           # (within 0.7 s, a press is a double tap: ignored)
        r = dictate()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.typed(), ["ydotool type --key-delay 2 -- Hello from the recording. "])
        self.assertEqual([p.name for p in (self.run / "dictate").glob("*.wav")], ["last.wav"])
        time.sleep(1.5)                           # the auto-stop timer (2 s) finds nothing to do
        log = self.log.read_text()
        self.assertEqual((log.count("record "), log.count("whisper ")), (1, 1), log)
        self.assertEqual(dictate("--status").stdout.strip(), "idle")

    def test_stopping_a_recording_ends_its_auto_stop_timer(self):
        """A recording stopped by a press left its auto-stop timer sleeping out MAX_SECONDS (300 by
        default) as a process of its own: it goes with the recording now."""
        dictate = self.dictate(300)
        self.stub(self.home / ".local/bin", "pw-record",                       # (records until stopped)
                  f'echo "record $*" >> {self.log}; for f; do :; done; echo RIFF > "$f"; exec sleep 30 >/dev/null 2>&1 </dev/null')
        self.assertEqual(dictate().returncode, 0)
        timer = int((self.run / "dictate/autostop.pid").read_text())
        os.kill(timer, 0)                                                     # (it's there)
        time.sleep(0.8)                           # (within 0.7 s, a press is a double tap: ignored)
        self.assertEqual(dictate().returncode, 0)
        for _ in range(60):
            try:
                os.kill(timer, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            self.fail("the auto-stop timer is still running")
        self.assertFalse((self.run / "dictate/autostop.pid").exists())


class DictationInstall(Home):
    def install(self, conf):
        """dictation/install.sh in a throwaway home with dictate.conf saying conf, the shared model
        there and two that older versions downloaded; stand-ins for Homebrew, systemctl and the
        ydotool helper's installer. The models left afterwards."""
        self.home = Path(tempfile.mkdtemp(dir=self.tmp))
        models = self.home / ".local/share/whisper"
        models.mkdir(parents=True)
        for m in ("ggml-small-q8_0.bin", "ggml-small.en-q5_1.bin", "ggml-base.en-q5_1.bin"):
            (models / m).write_text("")
        (self.home / ".config/frame-tweaks").mkdir(parents=True)
        (self.home / ".config/frame-tweaks/dictate.conf").write_text(conf)
        stubs, ydotool = self.tmp / "stubs", self.tmp / "ydotool"
        for name in ("brew", "systemctl"):
            self.stub(stubs, name, f'echo "{name} $*" >> {self.log}')
        self.stub(ydotool, "install.sh", f'echo "ydotool install" >> {self.log}')
        env = sandbox_env(self.home, stubs, BREW_BIN=stubs / "brew", FRAME_TWEAKS_DIRS=f"ydotool={ydotool}")
        r = subprocess.run(["bash", str(DICTATION / "install.sh")], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return sorted(p.name for p in models.iterdir())

    def test_old_models_go_unless_dictate_conf_uses_one(self):
        """The example settings (copied into every dictate.conf) name ggml-base.en-q5_1.bin in a
        comment: that kept it for ever. Only a setting in use keeps an old model."""
        example = (DICTATION / "dictate.conf.example").read_text()
        self.assertIn('#DICTATE_MODEL="$HOME/.local/share/whisper/ggml-base.en-q5_1.bin"', example)
        self.assertEqual(self.install(example), ["ggml-small-q8_0.bin"])
        used = example + 'DICTATE_MODEL="$HOME/.local/share/whisper/ggml-base.en-q5_1.bin"\n'
        self.assertEqual(self.install(used), ["ggml-base.en-q5_1.bin", "ggml-small-q8_0.bin"])
        self.assertEqual(self.install('  DICTATE_MODEL=~/.local/share/whisper/ggml-small.en-q5_1.bin\n'),
                         ["ggml-small-q8_0.bin", "ggml-small.en-q5_1.bin"])


class DictateTyping(Home):
    """The text goes to the focused window as typed keys. ydotool type assumes a US keyboard: on
    another layout (KDE's) letters and punctuation came out wrong (azerty: "a" typed "q"), so there
    each character's keys come from that layout (lib/xkb.py) and go out as ydotool key events, and
    text with a character the layout has no key for isn't typed at all: it's in the clipboard, as
    a notification says. One dictation each: started, then stopped and transcribed (stand-ins
    record, transcribe and type)."""

    def dictate(self, text, kxkbrc=None):
        run = self.tmp / "run"
        src = (DICTATION / "dictate").read_text()
        script = self.tmp / "dictate"
        script.write_text(src.replace("RUN=/run/user/$(id -u)\n", f"RUN={run}\n"))     # (not the real one)
        script.chmod(0o755)
        bin_ = self.home / ".local/bin"           # first on dictate's PATH: nothing real records, types or notifies
        self.stub(bin_, "pw-record", "exec sleep 30 >/dev/null 2>&1")      # (until stopped; not holding output open)
        self.stub(bin_, "pw-play", "exit 0")
        self.stub(bin_, "ffprobe", "echo 1.5")
        self.stub(bin_, "ffmpeg", 'echo "[Parsed_volumedetect_0] max_volume: -12.0 dB" >&2')
        self.stub(bin_, "whisper-cli", f"printf '%s\\n' {shlex.quote(text)}")
        self.stub(bin_, "wl-copy", f'echo "copied $(cat)" >> {self.log}')
        self.stub(bin_, "ydotool", f'echo "ydotool $*" >> {self.log}')
        self.stub(bin_, "notify-send", f'echo "notify $*" >> {self.log}')
        if kxkbrc:
            (self.home / ".config").mkdir(parents=True, exist_ok=True)
            (self.home / ".config/kxkbrc").write_text(kxkbrc)
        env = sandbox_env(self.home)
        for _ in ("start", "stop"):
            r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            time.sleep(0.8)                       # (a second press within 0.7 s is ignored)
        for _ in range(100):                      # (the stop runs the transcription in the background)
            if "notify" in self.log.read_text().split("copied", 1)[-1]:
                break
            time.sleep(0.1)
        return [line for line in self.log.read_text().splitlines() if line.split()[0] in ("ydotool", "notify", "copied")]

    def test_us_keyboard_types_as_before(self):
        log = self.dictate("Hello, world.")
        self.assertIn("ydotool type --key-delay 2 -- Hello, world. ", log)
        self.assertEqual(log[-1], "notify -a Dictation -t 1500 Copied to clipboard Hello, world. ")
        log = self.dictate("Hi", "[Layout]\nLayoutList=us\nUse=true\n")
        self.assertIn("ydotool type --key-delay 2 -- Hi", log)

    @unittest.skipUnless(xkb_compiles(), "needs libxkbcommon and XKB's layouts")
    def test_another_layout_types_its_keys(self):
        log = self.dictate("Qa?", "[Layout]\nLayoutList=fr\nUse=true\n")
        self.assertIn("copied Qa? ", log)                       # (a space after a sentence)
        self.assertIn("ydotool key --key-delay 11 42:1 30:1 30:0 42:0 16:1 16:0 42:1 50:1 50:0 42:0 57:1 57:0", log)
        self.assertFalse([line for line in log if line.startswith("ydotool type")])
        self.assertTrue(log[-1].startswith("notify -a Dictation -t 1500 Copied to clipboard"))

    @unittest.skipUnless(xkb_compiles(), "needs libxkbcommon and XKB's layouts")
    def test_a_character_the_layout_cant_type(self):
        log = self.dictate("Hola 漢字", "[Layout]\nLayoutList=latam\n")
        self.assertIn("copied Hola 漢字", log)
        self.assertFalse([line for line in log if line.startswith("ydotool")])        # nothing typed at all
        self.assertEqual(log[-1], "notify -a Dictation -t 1500 Not typed: copied to the clipboard "
                                  "Your keyboard layout has no key for 漢字. Paste the text instead (Ctrl+V).")


class DictateSettings(unittest.TestCase):
    def test_example_has_every_setting_the_readme_lists(self):
        readme = (DICTATION / "README.md").read_text().split("## Settings", 1)[1].split("\n## ", 1)[0]
        example = (DICTATION / "dictate.conf.example").read_text()
        listed = set(re.findall(r"^- `(DICTATE_[A-Z_]+)", readme, re.M))
        self.assertTrue(listed)
        self.assertEqual({k for k in listed if not re.search(rf"^#{k}=", example, re.M)}, set())


if __name__ == "__main__":
    unittest.main()
