"""adb-scrcpy/phone: which phone it connects to. Fake avahi-browse/kdialog/adb/scrcpy in a
throwaway home: one phone is taken and remembered, several are chosen from a list, a remembered
phone that's missing can be waited for or swapped."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHONE = ROOT / "adb-scrcpy" / "phone"


def advert(name, ip, port):
    return (f'=;wlan0;IPv4;adb-x;_adb-tls-connect._tcp;local;host.local;{ip};{port};'
            f'"name={name}" "api=37.0" "v=2.0"')


class PhonePick(unittest.TestCase):
    def run_phone(self, phones, conf=None, choose=None, args=(), old_place=False, extra=None, env=None):
        home = Path(self.tmp.name)
        stubs = home / ".local/bin"          # (first on phone's PATH, ahead of Homebrew's real scrcpy)
        stubs.mkdir(parents=True, exist_ok=True)
        (home / ".config/frame-tweaks").mkdir(parents=True, exist_ok=True)
        if conf is not None:
            (home / (".config/phone.conf" if old_place else ".config/frame-tweaks/phone.conf")).write_text(conf)
        log = home / "log"
        log.write_text("")
        scripts = {
            "avahi-browse": "printf '%s\\n' " + " ".join(f"'{advert(*p)}'" for p in phones),
            # kdialog --title T --menu TEXT tag label...: answer $CHOOSE (empty: closed)
            "kdialog": f'echo "kdialog $*" >> {log}; [ -n "$CHOOSE" ] && echo "$CHOOSE" || exit 1',
            "notify-send": f'echo "notify $*" >> {log}',
            "adb": f'echo "adb $*" >> {log}; [ "$1 $2" = "-s " ] || true; exit 0',
            "scrcpy": f'echo "scrcpy $*" >> {log}; exit 0',
            "sleep": "exit 0", "setsid": f'echo "setsid $*" >> {log}', "pgrep": "exit 1",
            **(extra or {}),
        }
        for name, body in scripts.items():
            (stubs / name).write_text(f"#!/bin/bash\n{body}\n")
            (stubs / name).chmod(0o755)
        env = {"HOME": str(home), "PATH": f"{stubs}:/usr/bin:/bin", "CHOOSE": choose or "", **(env or {})}
        r = subprocess.run(["bash", str(PHONE), *args], env=env, capture_output=True, text=True, timeout=30)
        f = home / ".config/frame-tweaks/phone.conf"
        conf_text = f.read_text() if f.exists() else ""
        return r.returncode, log.read_text(), conf_text

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_one_phone_is_taken_and_remembered(self):
        code, log, conf = self.run_phone([("Pixel 9", "10.0.0.5", 4000)])
        self.assertEqual(code, 0)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertIn("PHONE_NAME=Pixel\\ 9", conf)
        self.assertNotIn("kdialog", log)

    def test_several_phones_ask_and_remember_the_choice(self):
        phones = [("Pixel 9", "10.0.0.5", 4000), ("Galaxy S30", "10.0.0.6", 5000)]
        code, log, conf = self.run_phone(phones, choose="Galaxy S30")
        self.assertIn("--menu Which phone?", log)
        self.assertIn("scrcpy -s 10.0.0.6:5000", log)
        self.assertIn("PHONE_NAME=Galaxy\\ S30", conf)

    def test_closing_the_list_connects_nowhere(self):
        phones = [("Pixel 9", "10.0.0.5", 4000), ("Galaxy S30", "10.0.0.6", 5000)]
        code, log, conf = self.run_phone(phones, choose="")
        self.assertNotEqual(code, 0)
        self.assertNotIn("scrcpy", log)
        self.assertNotIn("PHONE_NAME", conf)

    def test_missing_phone_can_be_swapped_for_one_in_sight(self):
        code, log, conf = self.run_phone([("Galaxy S30", "10.0.0.6", 5000)], conf='PHONE_NAME="Pixel 9"\nPHONE_MAX_FPS=90\n',
                                         choose="Galaxy S30")
        self.assertIn("Use Galaxy S30 instead", log)
        self.assertIn("scrcpy -s 10.0.0.6:5000", log)
        self.assertEqual(conf.count("PHONE_NAME"), 1)
        self.assertIn("PHONE_MAX_FPS=90", conf)                    # other settings kept

    def test_missing_phone_with_none_in_sight_is_waited_for(self):
        code, log, conf = self.run_phone([], conf='PHONE_NAME="Pixel 9"\n')
        self.assertNotEqual(code, 0)                               # (fake: it never shows up)
        self.assertIn("notify -a Phone Waiting for Pixel 9", log)
        self.assertIn("didn't appear", log)
        self.assertNotIn("kdialog", log)

    def test_settings_in_the_old_place_are_moved(self):
        code, log, conf = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf='PHONE_NAME="Pixel 9"\nPHONE_MAX_FPS=90\n',
                                         old_place=True)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertIn("--max-fps=90", log)
        self.assertIn("PHONE_MAX_FPS=90", conf)
        self.assertFalse((Path(self.tmp.name) / ".config/phone.conf").exists())

    def test_pick_asks_even_with_a_remembered_phone(self):
        phones = [("Pixel 9", "10.0.0.5", 4000)]
        code, log, conf = self.run_phone(phones, conf='PHONE_NAME="Galaxy S30"\n', choose="Pixel 9", args=["--pick"])
        self.assertIn("--menu Which phone?", log)
        self.assertIn("PHONE_NAME=Pixel\\ 9", conf)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)

    def test_vr_extras_start_with_a_tested_scrcpy(self):
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], env={"DISPLAY": ":0"},
                                      extra={"phone-touch": "exit 0", "phone-fit": "exit 0"})
        self.assertIn("bin/phone-fit", log)
        self.assertIn("bin/phone-touch 10.0.0.5:4000", log)

    def test_untested_scrcpy_gets_a_plain_window(self):
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], env={"DISPLAY": ":0"},
                                      extra={"phone-touch": '[ "$1" = --check ] && exit 1', "phone-fit": "exit 0"})
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertNotIn("phone-fit", log)                         # no narrow window: clicks land right
        self.assertNotIn("phone-touch 10.0.0.5", log)


if __name__ == "__main__":
    unittest.main()
