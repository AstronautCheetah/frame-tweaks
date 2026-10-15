"""The Speech engine's installer and Dictation's toggle, in a throwaway home with stand-ins for
the tools that would download, record, play or notify. A speech.conf without a language (only
the engine chosen, or reset) is English (US): nothing to download, a real language for
speech-dispatcher. A recording that ended by itself isn't "auto-stopped" into a new one. Every
setting the README lists is in the example settings file."""
import sys
import os
import re
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
SPEECH = ROOT / "packs/original/speech"
DICTATION = ROOT / "packs/original/dictation"


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
    def install(self, conf):
        self.home = Path(tempfile.mkdtemp(dir=self.tmp))
        self.log.write_text("")
        d = self.home / ".local/share/frame-tweaks/speech"
        # Installed already: Piper at the pinned version and the English (US) voice
        self.stub(d / "piper", "piper", "exit 0")
        (d / "piper/.version").write_text(pin(SPEECH / "pin", "version") + "\n")
        for f in ("voice.onnx", "voice.onnx.json"):
            (d / f).write_text("")
        (d / "voice.version").write_text(pin(SPEECH / "voice.pin", "version") + "\n")
        (self.home / ".config/frame-tweaks").mkdir(parents=True)
        (self.home / ".config/frame-tweaks/speech.conf").write_text(conf)
        stubs = self.tmp / "stubs"     # no network; and never the real speech-dispatcher
        self.stub(stubs, "curl", f'echo "curl $*" >> {self.log}; exit 7')
        self.stub(stubs, "pkill", f'echo "pkill $*" >> {self.log}')
        env = sandbox_env(self.home, stubs)
        r = subprocess.run(["bash", str(SPEECH / "install.sh")], env=env, capture_output=True, text=True, timeout=60)
        return r, d

    def test_no_language_set_is_english_us(self):
        for conf, engine in (("SPEECH_ENGINE=espeak-ng\n", "espeak-ng"), ("", "piper")):   # engine chosen; reset
            with self.subTest(conf=conf):
                r, d = self.install(conf)
                self.assertNotIn("curl", self.log.read_text(), r.stdout + r.stderr)    # the voice it has
                narrate = (d / "narrate.conf").read_text()
                self.assertIn(f"engine={engine}\n", narrate)
                self.assertIn("language=en_US\n", narrate)
                self.assertIn("espeak_voice=en-us\n", narrate)
                if Path("/etc/speech-dispatcher/speechd.conf").is_file() and \
                        Path("/etc/speech-dispatcher/modules/espeak-ng.conf").is_file():   # (SteamOS has them)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    sd = (self.home / ".config/speech-dispatcher/speechd.conf").read_text()
                    self.assertIn('DefaultLanguage "en"', sd)


class DictateAutoStop(Home):
    def test_a_recording_that_ended_by_itself_isnt_restarted(self):
        """pw-record ended on its own (here: at once). The auto-stop timer then finds nothing to
        stop; it must not run the toggle, which would start a new recording."""
        run = self.tmp / "run"
        src = (DICTATION / "dictate").read_text()
        self.assertIn("RUN=/run/user/$(id -u)\n", src)
        script = self.tmp / "dictate"
        script.write_text(src.replace("RUN=/run/user/$(id -u)\n", f"RUN={run}\n"))     # (not the real one)
        script.chmod(0o755)
        bin_ = self.home / ".local/bin"           # first on dictate's PATH: nothing real records, plays or notifies
        self.stub(bin_, "pw-record", f'echo "record $*" >> {self.log}')
        self.stub(bin_, "pw-play", "exit 0")
        self.stub(bin_, "notify-send", f'echo "notify $*" >> {self.log}')
        (self.home / ".config/frame-tweaks").mkdir(parents=True)
        (self.home / ".config/frame-tweaks/dictate.conf").write_text("DICTATE_MAX_SECONDS=1\n")
        env = sandbox_env(self.home)
        r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        time.sleep(2.5)                           # the auto-stop timer (1 s) has run
        log = self.log.read_text()
        self.assertEqual(log.count("record "), 1, log)
        status = subprocess.run(["bash", str(script), "--status"], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(status.stdout.strip(), "idle")


class DictateSettings(unittest.TestCase):
    def test_example_has_every_setting_the_readme_lists(self):
        readme = (DICTATION / "README.md").read_text().split("## Settings", 1)[1].split("\n## ", 1)[0]
        example = (DICTATION / "dictate.conf.example").read_text()
        listed = set(re.findall(r"^- `(DICTATE_[A-Z_]+)", readme, re.M))
        self.assertTrue(listed)
        self.assertEqual({k for k in listed if not re.search(rf"^#{k}=", example, re.M)}, set())


if __name__ == "__main__":
    unittest.main()
