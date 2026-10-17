"""adb-scrcpy/phone: which phone it connects to. Fake avahi-browse/kdialog/adb/scrcpy in a
throwaway home: one phone is taken and remembered, several are chosen from a list, a remembered
phone that's missing can be waited for or swapped; Restart stream after Reset to defaults. And
the tweak's uninstall stopping adb's server in both sessions."""
import sys
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
PHONE = ROOT / "packs/core/adb-scrcpy" / "phone"


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
            stub(stubs, name, body)
        (home / "run").mkdir(exist_ok=True)      # (its pid file and scrcpy's log: not a running mirror's)
        env = sandbox_env(home, stubs, **{"CHOOSE": choose or "", "XDG_RUNTIME_DIR": home / "run",
                                          "PHONE_NO_SPLASH": 1, **(env or {})})   # (the splash has a test of its own)
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
        # Never the mirror window's own title, which the VR dashboard's patches go by (a splash
        # with it was taken for the mirror after a stream restart, and left over it)
        self.assertIn("--title Android Mirror setup --progressbar", lines[0])
        self.assertNotIn("--title Android Mirror --", log)

    def test_settings_in_the_old_place_are_moved(self):
        code, log, conf = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf='PHONE_NAME="Pixel 9"\nPHONE_MAX_FPS=90\n',
                                         old_place=True)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertIn("--max-fps=90", log)
        self.assertIn("PHONE_MAX_FPS=90", conf)
        self.assertFalse((Path(self.tmp.name) / ".config/phone.conf").exists())

    def test_clipboard_shared_unless_set_not_to(self):
        """PHONE_CLIPBOARD=off: scrcpy keeps the phone's clipboard and the Frame's apart."""
        for conf, flagged in (("", False), ("PHONE_CLIPBOARD=both\n", False), ("PHONE_CLIPBOARD=off\n", True)):
            code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf='PHONE_NAME="Pixel 9"\n' + conf)
            self.assertIn("scrcpy -s 10.0.0.5:4000", log, conf)
            self.assertEqual("--no-clipboard-autosync" in log, flagged, conf)

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

    def test_restart_after_reset_to_defaults_uses_the_defaults(self):
        """The gear's Reset to defaults takes the settings' lines out of phone.conf, then Restart
        stream: the new stream is at the defaults (reading the file again can't unset what the
        file no longer says)."""
        conf = ('PHONE_NAME="Pixel 9"\nPHONE_MAX_SIZE=1920\nPHONE_BIT_RATE=8M\nPHONE_MAX_FPS=90\n'
                'PHONE_STICK_SPEED=25\nPHONE_CLIPBOARD=off\n')
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf=conf, extra={
            # the first mirror: Reset to defaults, then Restart stream (phone-touch's SIGUSR1), and
            # it runs until it's stopped; the restarted one closes
            "scrcpy": 'echo "scrcpy $*" >> "$HOME/log"; [ -f "$HOME/reset" ] && exit 0; touch "$HOME/reset"; '
                      '/usr/bin/sleep 0.5; printf \'PHONE_NAME="Pixel 9"\\n\' > "$HOME/.config/frame-tweaks/phone.conf"; '
                      'kill -USR1 "$(cat "$XDG_RUNTIME_DIR/sft-phone.pid")"; exec /usr/bin/sleep 10',
            "sleep": "exec /usr/bin/sleep 0.05"})
        self.assertEqual(code, 0, log)
        runs = [l for l in log.splitlines() if l.startswith("scrcpy ")]
        self.assertEqual(len(runs), 2, log)
        self.assertIn("--video-bit-rate=8M --max-size=1920 --max-fps=90 --no-clipboard-autosync", runs[0])
        self.assertIn("--video-bit-rate=2M --max-size=1024 --max-fps=60 --window-title", runs[1])

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


class AutoDisconnect(unittest.TestCase):
    """A mirror left on drained the phone's battery overnight: after PHONE_TIMEOUT minutes it asks
    (a minute) whether to keep it on, and with no answer closes the mirror and disconnects. Minutes
    are seconds here (PHONE_MINUTE); the mirror runs until it's stopped."""
    setUp, run_phone = PhonePick.setUp, PhonePick.run_phone
    PHONES = [("Pixel 9", "10.0.0.5", 4000)]
    MIRROR = 'echo "scrcpy $*" >> "$HOME/log"; exec /usr/bin/sleep 20'
    # kdialog --yesno: logged with the time; answers from $HOME/answers (one per ask: yes, no; none
    # left: never answers)
    ASK = ('echo "kdialog $(date +%s.%N) $*" >> "$HOME/log"; a=$(head -1 "$HOME/answers" 2>/dev/null); '
           'sed -i 1d "$HOME/answers" 2>/dev/null; case "$a" in yes) exit 0;; no) exit 1;; esac; exec /usr/bin/sleep 20')

    def run_auto(self, conf, answers="", mirror=None, minute=1):
        (Path(self.tmp.name) / "answers").write_text(answers)
        return self.run_phone(self.PHONES, conf='PHONE_NAME="Pixel 9"\n' + conf, env={"PHONE_MINUTE": minute}, extra={
            "scrcpy": mirror or self.MIRROR, "kdialog": self.ASK, "sleep": "exec /usr/bin/sleep 0.05",
            "notify-send": 'echo "notify $*" >> "$HOME/log"'})

    def test_no_answer_disconnects(self):
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n")
        self.assertEqual(code, 0, log)
        self.assertEqual(log.count("--yesno"), 1, log)
        self.assertIn("Keep it on", log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)
        self.assertIn("notify -a Phone Android Mirror disconnected Pixel 9 was mirrored for 1 min", log)
        self.assertNotIn("--title Android Mirror --", log)           # (the mirror window's own title)

    def test_keep_it_on_asks_again_after_the_same_time(self):
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n", answers="yes\n")
        self.assertEqual(log.count("--yesno"), 2, log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)

    def test_disconnect_answer_goes_at_once(self):
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n", answers="no\n")
        self.assertEqual(log.count("--yesno"), 1, log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)

    def test_never(self):
        """PHONE_TIMEOUT=0: the mirror stays until it's closed."""
        code, log, _ = self.run_auto("PHONE_TIMEOUT=0\n", mirror='echo "scrcpy $*" >> "$HOME/log"; /usr/bin/sleep 2.5')
        self.assertEqual(code, 0, log)
        self.assertNotIn("--yesno", log)
        self.assertNotIn("adb disconnect", log)

    def test_a_change_counts_from_then(self):
        """Changed while the mirror is open (the gear, the settings page): it applies to that mirror,
        counted from the change (1 minute set after 2.5 minutes open doesn't disconnect at once)."""
        conf = Path(self.tmp.name) / ".config/frame-tweaks/phone.conf"
        code, log, _ = self.run_auto("PHONE_TIMEOUT=0\n", minute=2, mirror=(
            'echo "scrcpy $*" >> "$HOME/log"; /usr/bin/sleep 2.5; '
            f'echo PHONE_TIMEOUT=1 >> "{conf}"; echo "changed $(date +%s.%N)" >> "$HOME/log"; exec /usr/bin/sleep 20'))
        changed = float(next(l.split()[1] for l in log.splitlines() if l.startswith("changed ")))
        asked = float(next(l.split()[1] for l in log.splitlines() if "--yesno" in l))
        self.assertGreaterEqual(asked - changed, 1.0, log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)

    def test_reset_to_defaults_is_back_to_an_hour(self):
        """Reset to defaults takes PHONE_TIMEOUT out of the file: an hour again, not the value the
        mirror started with."""
        conf = Path(self.tmp.name) / ".config/frame-tweaks/phone.conf"
        code, log, _ = self.run_auto("PHONE_TIMEOUT=2\n", mirror=(
            'echo "scrcpy $*" >> "$HOME/log"; /usr/bin/sleep 0.5; '
            f'printf \'PHONE_NAME="Pixel 9"\\n\' > "{conf}"; /usr/bin/sleep 3.5'))
        self.assertEqual(code, 0, log)
        self.assertNotIn("--yesno", log)
        self.assertNotIn("adb disconnect", log)


class Uninstall(unittest.TestCase):
    def test_stops_adbs_server_in_both_sessions(self):
        """Each session starts its own adb server, its socket in that session's runtime folder
        (the adb wrapper's): VR's, and desktop mode's inside it (nested_plasma). Uninstalling
        from either stops both; it stopped only its own session's."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home = Path(tmp.name)
        run = home / "run"                        # (the runtime folders: never the real ones)
        (run / "nested_plasma").mkdir(parents=True)
        for sock in (run / "adb.sock", run / "nested_plasma/adb.sock"):
            os.mknod(sock, stat.S_IFSOCK | 0o600)
        wrapper = re.search(r"write_file \"\$BIN/adb\" 755 <<'EOS'\n#!/bin/sh\n(.*?\n)EOS\n",
                            (ROOT / "packs/core/adb-scrcpy/install.sh").read_text(), re.S)[1]
        log = home / "log"
        for session in (run, run / "nested_plasma"):
            with self.subTest(session=session.name):
                # adb as install.sh writes it; its adb.bin a stand-in saying which server it's asked to stop
                stub(home / ".local/bin", "adb", wrapper)
                stub(home / ".local/lib/android-tools", "adb.bin", f'echo "$ADB_SERVER_SOCKET $*" >> {log}')
                log.write_text("")
                env = sandbox_env(home, home / "stubs", XDG_RUNTIME_DIR=session)
                r = subprocess.run(["bash", str(ROOT / "packs/core/adb-scrcpy/uninstall.sh")], env=env,
                                   capture_output=True, text=True, timeout=30)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                stopped = set(log.read_text().splitlines())
                self.assertLessEqual({f"localfilesystem:{run}/adb.sock kill-server",
                                      f"localfilesystem:{run}/nested_plasma/adb.sock kill-server"}, stopped)


if __name__ == "__main__":
    unittest.main()
