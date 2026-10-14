"""adb-scrcpy/phone: which phone it connects to. Fake avahi-browse/kdialog/adb/scrcpy in a
throwaway home: one phone is taken and remembered, several are chosen from a list, a remembered
phone that's missing can be waited for or swapped."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHONE = ROOT / "packs/original/adb-scrcpy" / "phone"


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
            "adb": f'echo "adb $*" >> {log}; [ "$1" = connect ] && echo "connected to $2"; exit 0',
            "scrcpy": f'echo "scrcpy $*" >> {log}; exit 0',
            "sleep": "exit 0", "setsid": f'echo "setsid $*" >> {log}', "pgrep": "exit 1",
            **(extra or {}),
        }
        for name, body in scripts.items():
            (stubs / name).write_text(f"#!/bin/bash\n{body}\n")
            (stubs / name).chmod(0o755)
        (home / "run").mkdir(exist_ok=True)      # (its pid file and scrcpy's log: not a running mirror's)
        env = {"HOME": str(home), "PATH": f"{stubs}:/usr/bin:/bin", "CHOOSE": choose or "",
               "XDG_RUNTIME_DIR": str(home / "run"), "PHONE_NO_SPLASH": "1", **(env or {})}   # (the splash has a test of its own)
        r = subprocess.run(["bash", str(PHONE), *args], env=env, capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL)
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
        self.assertTrue((Path(self.tmp.name) / "run/phone-scrcpy.log").exists())   # in the session's runtime folder

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
        self.assertIn("Pixel 9 didn't appear", log)
        self.assertNotIn("--menu", log)                            # nothing else to choose
        self.assertIn("--error", log)                              # it says why it stopped

    def test_failed_connection_offers_pairing_again(self):
        """adb can't connect (the phone forgot the Frame): Pair it again finds the phone's pairing
        port on the Wi-Fi, asks only for the code, pairs, and the mirror starts."""
        pairing = "=;wlan0;IPv4;adb-x;_adb-tls-pairing._tcp;local;host.local;10.0.0.5;37001;"
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf='PHONE_NAME="Pixel 9"\n', choose="pair", extra={
            # the connect advert as usual; the pairing one when asked for _adb-tls-pairing
            "avahi-browse": f'''case "$*" in *pairing*) echo '{pairing}';; *) printf '%s\\n' '{advert("Pixel 9", "10.0.0.5", 4000)}';; esac''',
            "kdialog": 'echo "kdialog $*" >> "$HOME/log"; case "$*" in *--inputbox*) echo 123456;; *) echo "$CHOOSE";; esac',
            "adb": 'echo "adb $*" >> "$HOME/log"; case "$1" in connect) [ -f "$HOME/paired" ] && echo "connected to $2" || echo "failed to connect to $2";; '
                   'pair) printf "Enter pairing code: "; read -r c; echo "code $c" >> "$HOME/log"; touch "$HOME/paired"; echo "Successfully paired to $2";; esac; exit 0'})
        self.assertIn("Pair it again", log)
        self.assertIn("adb pair 10.0.0.5:37001\n", log)            # the code isn't on its command line,
        self.assertIn("code 123456", log)                          # it's typed in
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)

    def test_a_phone_named_like_another_isnt_taken_for_it(self):
        """The remembered "Pixel 9" isn't "Pixel 9 Pro" (it was matched as part of the name)."""
        phones = [("Pixel 9 Pro", "10.0.0.7", 4100), ("Pixel 9", "10.0.0.5", 4000)]
        code, log, _ = self.run_phone(phones, conf='PHONE_NAME="Pixel 9"\n')
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertNotIn("10.0.0.7", log)
        code, log, _ = self.run_phone(phones[:1], conf='PHONE_NAME="Pixel 9"\n', choose="")
        self.assertIn("Use Pixel 9 Pro instead", log)              # not in sight: wait, or use the other
        self.assertNotIn("scrcpy", log)

    def test_a_look_on_the_wifi_that_never_ends_is_cut_short(self):
        """avahi-browse can wait for an answer for ever (a mirror once waited a day): each look
        has a time limit, and what it found by then counts."""
        code, log, _ = self.run_phone([], conf='PHONE_NAME="Pixel 9"\n', extra={
            "avahi-browse": f"printf '%s\\n' '{advert('Pixel 9', '10.0.0.5', 4000)}'; exec /usr/bin/sleep 60",
            # (records the limit asked for, then keeps 1 s of it)
            "timeout": 'echo "timeout $1 $2" >> "$HOME/log"; shift; exec /usr/bin/timeout 1 "$@"'})
        self.assertIn("timeout 10 avahi-browse", log)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)

    def test_splash_closes_once_a_reconnected_mirror_is_up(self):
        """After a reconnect (or a restart), the splash went on showing "Starting the mirror…"
        for as long as the mirror ran."""
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf='PHONE_NAME="Pixel 9"\n', env={"PHONE_NO_SPLASH": ""}, extra={
            # each splash its own D-Bus name
            "kdialog": 'echo "kdialog $*" >> "$HOME/log"; case "$*" in *--progressbar*) n=$(( $(cat "$HOME/n" 2>/dev/null || echo 0) + 1 )); '
                       'echo $n > "$HOME/n"; echo "org.kde.kdialog-$n /ProgressDialog";; esac',
            "qdbus6": 'echo "qdbus6 $*" >> "$HOME/log"',
            # the first mirror loses the phone (it stops answering until reconnected); the second runs a moment
            "scrcpy": 'if [ ! -f "$HOME/dropped" ]; then /usr/bin/sleep 0.3; touch "$HOME/dropped"; exit 1; fi; '
                      'echo "mirror up" >> "$HOME/log"; /usr/bin/sleep 1.5; echo "mirror closed" >> "$HOME/log"',
            "adb": 'echo "adb $*" >> "$HOME/log"; case "$1 $3" in "connect "*) [ -f "$HOME/dropped" ] && touch "$HOME/back"; echo "connected to $2";; '
                   '*shell*) [ ! -f "$HOME/dropped" ] || [ -f "$HOME/back" ];; esac'})
        self.assertEqual(code, 0)
        lines = log.splitlines()
        self.assertTrue(any("Reconnecting" in l for l in lines))
        last = [l for l in lines if "--progressbar" in l][-1]
        self.assertIn("Connecting to Pixel 9", last)
        n = sum("--progressbar" in l for l in lines)
        close = lines.index(f"qdbus6 org.kde.kdialog-{n} /ProgressDialog close")
        self.assertLess(close, lines.index("mirror closed"))         # gone while the mirror runs

    def test_failed_connection_can_forget_the_phone(self):
        code, log, conf = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf='PHONE_NAME="Pixel 9"\nPHONE_MAX_FPS=90\n',
                                         choose="forget", extra={
            "adb": 'echo "adb $*" >> "$HOME/log"; [ "$1" = connect ] && echo "failed to connect to $2"; exit 0'})
        self.assertEqual(code, 0)
        self.assertIn("Forget Pixel 9", log)
        self.assertNotIn("PHONE_NAME", conf)
        self.assertIn("PHONE_MAX_FPS=90", conf)                    # other settings kept
        self.assertNotIn("scrcpy", log)

    def test_splash_then_a_message_saying_why(self):
        """No phone in sight: the splash shows, then closes, and an error dialog explains."""
        code, log, _ = self.run_phone([], env={"PHONE_NO_SPLASH": ""}, extra={
            "kdialog": 'echo "kdialog $*" >> "$HOME/log"; case "$*" in *--progressbar*) echo "org.kde.kdialog-1 /ProgressDialog";; esac',
            "qdbus6": 'echo "qdbus6 $*" >> "$HOME/log"'})
        self.assertNotEqual(code, 0)
        lines = log.splitlines()
        self.assertIn("--progressbar", lines[0])
        close = next(i for i, l in enumerate(lines) if l.endswith("/ProgressDialog close"))
        error = next(i for i, l in enumerate(lines) if "--error" in l)
        self.assertLess(close, error)                              # splash gone, then the message
        self.assertIn("No phone found", lines[error])

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

    def test_steamvr_update_that_turns_its_patch_off_gets_a_plain_window(self):
        """vr-dashboard switched the layer's patch off: the narrow window had no layer to take the
        clicks, so they landed at its left edge."""
        (Path(self.tmp.name) / "run").mkdir()
        (Path(self.tmp.name) / "run/sft-dashboard.status").write_text(
            "phone-touch: SteamVR changed (missing: frame panel height); off\n")
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], env={"DISPLAY": ":0"},
                                      extra={"phone-touch": "exit 0", "phone-fit": "exit 0"})
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertNotIn("phone-fit", log)
        self.assertNotIn("phone-touch 10.0.0.5", log)


if __name__ == "__main__":
    unittest.main()
