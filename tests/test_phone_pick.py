"""adb-scrcpy/phone: which phone it connects to. Fake avahi-browse/kdialog/adb/scrcpy in a
throwaway home: one phone is taken and remembered, several are chosen from a list, a remembered
phone that's missing can be waited for or swapped; it's known by its adb identity, so a device
announcing its name isn't taken for it, and two claiming it are told apart only by the address
you choose; Restart stream after Reset to defaults. And the tweak's uninstall stopping adb's
server in both sessions."""
import sys
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402
PHONE = ROOT / "packs/core/adb-scrcpy" / "phone"


def advert(name, ip, port, ident=None):
    """A phone's wireless debugging, as avahi-browse -rtp shows it. Its service's name (field 4) is
    its adb identity, adb-<serial>-<random>: its own, unless given."""
    ident = ident or "adb-" + re.sub(r"\W", "", name) + "-a1B2c3"
    return (f'=;wlan0;IPv4;{ident};_adb-tls-connect._tcp;local;host.local;{ip};{port};'
            f'"name={name}" "api=37.0" "v=2.0"')


REAL = ("Pixel 9", "10.0.0.5", 4000, "adb-SERIAL1-AbC123")
IMPOSTOR = ("Pixel 9", "10.0.0.66", 5555, "adb-OTHER-XyZ789")       # (its name, not its identity)


class PhonePick(unittest.TestCase):
    def run_phone(self, phones, conf=None, choose=None, args=(), old_place=False, extra=None, env=None,
                  path=("/usr/bin", "/bin"), timeout=30):
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
            if body is not None:                 # (None: no such command)
                stub(stubs, name, body)
        (home / "run").mkdir(exist_ok=True)      # (its pid file and scrcpy's log: not a running mirror's)
        env = sandbox_env(home, stubs, path, **{"CHOOSE": choose or "", "XDG_RUNTIME_DIR": home / "run",
                                                "PHONE_NO_SPLASH": 1, **(env or {})})   # (the splash has a test of its own)
        r = subprocess.run(["bash", str(PHONE), *args], env=env, capture_output=True, text=True, timeout=timeout,
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
        # (minutes after it was opened, it says whose message it is: in the text too, as VR shows
        # no title bar, and in the notification)
        self.assertIn("--error Android Mirror: Pixel 9 didn't appear\n\nIt didn't turn up", log)
        self.assertIn("notify -a Android Mirror Android Mirror: Pixel 9 didn't appear", log)

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
        # (paired again, it keeps its identity: Android does too, so it's found by it next time)
        conf = (Path(self.tmp.name) / ".config/frame-tweaks/phone.conf").read_text()
        self.assertIn("PHONE_ID=adb-Pixel9-a1B2c3\n", conf)

    def test_a_phone_named_like_another_isnt_taken_for_it(self):
        """The remembered "Pixel 9" isn't "Pixel 9 Pro" (it was matched as part of the name)."""
        phones = [("Pixel 9 Pro", "10.0.0.7", 4100), ("Pixel 9", "10.0.0.5", 4000)]
        code, log, _ = self.run_phone(phones, conf='PHONE_NAME="Pixel 9"\n')
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertNotIn("10.0.0.7", log)
        code, log, _ = self.run_phone(phones[:1], conf='PHONE_NAME="Pixel 9"\n', choose="")
        self.assertIn("Use Pixel 9 Pro instead", log)              # not in sight: wait, or use the other
        self.assertNotIn("scrcpy", log)

    def test_a_device_announcing_its_name_isnt_taken_for_it(self):
        """Found by its name (remembered by an older version), the phone is known by its adb
        identity from then on: another device announcing the same name, ahead of it in the list,
        isn't connected to (the first one with the name was). The phone's new port (Wireless
        debugging turned off and on) is followed."""
        code, log, conf = self.run_phone([REAL], conf='PHONE_NAME="Pixel 9"\n')
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertIn("PHONE_ID=adb-SERIAL1-AbC123\n", conf)
        self.assertIn("PHONE_ADDRESS=10.0.0.5:4000\n", conf)
        code, log, conf = self.run_phone([IMPOSTOR, (*REAL[:2], 4100, REAL[3])])
        self.assertEqual(code, 0, log)
        self.assertIn("scrcpy -s 10.0.0.5:4100", log)
        self.assertNotIn("10.0.0.66", log)
        self.assertNotIn("--menu", log)
        self.assertIn("PHONE_ADDRESS=10.0.0.5:4100\n", conf)

    def test_its_name_with_another_identity_is_asked_about(self):
        """The phone isn't in sight but something with its name is (another phone with that name,
        the same one after a factory reset, a device posing as it): not taken by itself. Chosen,
        it's the phone from now on."""
        conf = 'PHONE_NAME="Pixel 9"\nPHONE_ID=adb-SERIAL1-AbC123\n'
        code, log, _ = self.run_phone([IMPOSTOR], conf=conf, choose="")
        self.assertNotEqual(code, 0)
        self.assertIn("isn't the phone Android Mirror knows by that name", log)
        self.assertIn("Use this other Pixel 9", log)
        self.assertNotIn("adb connect", log)
        self.assertNotIn("scrcpy", log)
        code, log, conf = self.run_phone([IMPOSTOR], conf=conf, choose="Pixel 9")
        self.assertIn("scrcpy -s 10.0.0.66:5555", log)
        self.assertIn("PHONE_ID=adb-OTHER-XyZ789\n", conf)
        self.assertEqual(conf.count("PHONE_ID"), 1)

    def test_two_claiming_it_connect_to_neither_unless_chosen(self):
        """Two advertisements with the phone's identity (one posing as it): neither is connected to
        by itself. You choose the address the phone shows; while it's there, it's taken again
        without asking."""
        conf = 'PHONE_NAME="Pixel 9"\nPHONE_ID=adb-SERIAL1-AbC123\n'
        twins = [(*IMPOSTOR[:3], REAL[3]), REAL]
        code, log, _ = self.run_phone(twins, conf=conf, choose="")
        self.assertNotEqual(code, 0)
        self.assertIn("More than one device on the Wi-Fi says it's Pixel 9", log)
        self.assertIn("10.0.0.5:4000 10.0.0.5:4000 10.0.0.66:5555 10.0.0.66:5555", log)   # (by address)
        self.assertNotIn("adb connect", log)
        self.assertNotIn("scrcpy", log)
        code, log, conf = self.run_phone(twins, conf=conf, choose="10.0.0.5:4000")
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertNotIn("adb connect 10.0.0.66", log)
        self.assertIn("PHONE_ADDRESS=10.0.0.5:4000\n", conf)
        code, log, _ = self.run_phone(twins)
        self.assertNotIn("--menu", log)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)

    def test_two_claiming_it_without_kdialog_connect_to_neither(self):
        """No kdialog to choose with: it stops and says why (a notification) rather than take
        one. (On a PATH of only the commands it needs: this Frame's kdialog stays out of it.)"""
        tools = Path(self.tmp.name) / "tools"
        tools.mkdir()
        for name in ("bash", "awk", "grep", "sed", "sort", "cut", "timeout", "cat", "id", "mkdir", "date", "seq",
                     "rm", "mv", "tr", "head", "tail", "paste"):
            (tools / name).symlink_to(shutil.which(name, path="/usr/bin:/bin"))
        conf = 'PHONE_NAME="Pixel 9"\nPHONE_ID=adb-SERIAL1-AbC123\n'
        code, log, _ = self.run_phone([(*IMPOSTOR[:3], REAL[3]), REAL], conf=conf, extra={"kdialog": None},
                                      path=(str(tools),))
        self.assertNotEqual(code, 0)
        self.assertIn("notify -a Android Mirror Android Mirror: More than one Pixel 9 More than one device on the Wi-Fi says it's Pixel 9", log)
        self.assertNotIn("kdialog", log)
        self.assertNotIn("adb connect", log)
        self.assertNotIn("scrcpy", log)

    def test_its_identity_is_remembered_once_it_has_connected(self):
        """Remembered by its name only (by an older version), and a device announcing that name is
        alone on the Wi-Fi: its identity was remembered before connecting, so when it didn't connect
        (it only announces the name), the phone itself was "not the phone Android Mirror knows"
        from then on."""
        refuses = {"adb": 'echo "adb $*" >> "$HOME/log"; [ "$1" = connect ] && echo "failed to connect to $2"; exit 0'}
        code, log, conf = self.run_phone([IMPOSTOR], conf='PHONE_NAME="Pixel 9"\n', choose="close", extra=refuses)
        self.assertNotEqual(code, 0)
        self.assertIn("adb connect 10.0.0.66:5555", log)
        self.assertNotIn("PHONE_ID", conf)
        code, log, conf = self.run_phone([REAL])
        self.assertEqual(code, 0, log)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertNotIn("isn't the phone", log)
        self.assertIn("PHONE_ID=adb-SERIAL1-AbC123\n", conf)

    def test_a_service_renamed_by_mdns_counts_as_claiming_it(self):
        """mDNS renames a service whose name another device took first ("ID (2)", as avahi escapes
        it): that's the phone's too, so two claim it; alone, it's the phone."""
        renamed = REAL[3] + "\\032\\0402\\041"
        conf = 'PHONE_NAME="Pixel 9"\nPHONE_ID=adb-SERIAL1-AbC123\n'
        code, log, _ = self.run_phone([(*IMPOSTOR[:3], REAL[3]), (*REAL[:3], renamed)], conf=conf, choose="")
        self.assertIn("More than one device", log)
        self.assertNotIn("scrcpy", log)
        code, log, conf = self.run_phone([(*REAL[:3], renamed)], conf=conf)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertIn("PHONE_ID=adb-SERIAL1-AbC123\n", conf)      # (its own name, not the renamed one)

    def test_two_phones_with_one_name_are_told_apart_by_address(self):
        """Remembered by name only, and two phones announce it: the one at the address you choose
        is the phone, by its identity from then on."""
        code, log, conf = self.run_phone([IMPOSTOR, REAL], conf='PHONE_NAME="Pixel 9"\n', choose="10.0.0.5:4000")
        self.assertIn("More than one device on the Wi-Fi says it's Pixel 9", log)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)
        self.assertIn("PHONE_ID=adb-SERIAL1-AbC123\n", conf)

    def test_forget_forgets_its_identity_and_address_too(self):
        code, log, conf = self.run_phone([], conf='PHONE_NAME="Pixel 9"\nPHONE_ID=adb-SERIAL1-AbC123\n'
                                                  'PHONE_ADDRESS=10.0.0.5:4000\nPHONE_MAX_FPS=90\n', args=["--forget"])
        self.assertEqual(code, 0)
        self.assertEqual(conf, "PHONE_MAX_FPS=90\n")

    def test_a_look_on_the_wifi_that_never_ends_is_cut_short(self):
        """avahi-browse can wait for an answer for ever (a mirror once waited a day): each look
        has a time limit, and what it found by then counts."""
        code, log, _ = self.run_phone([], conf='PHONE_NAME="Pixel 9"\n', extra={
            "avahi-browse": f"printf '%s\\n' '{advert('Pixel 9', '10.0.0.5', 4000)}'; exec /usr/bin/sleep 60",
            # (records the limit asked for, then keeps 3 s of it: time enough, on a busy test machine,
            # for the stand-in to print its phone before it's cut short)
            "timeout": 'echo "timeout $1 $2" >> "$HOME/log"; shift; exec /usr/bin/timeout 3 "$@"'})
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
            # the first mirror loses the phone (it stops answering until reconnected) once it's being
            # watched (adb shell: past the start-up check, which takes a mirror gone by then for one
            # that didn't start); the second closes once its splash is closed, or after 10 s (the
            # splash left open: the bug). Waiting on these, not fixed times: a busy test machine
            # once took longer than them.
            "scrcpy": 'if [ ! -f "$HOME/dropped" ]; then for _ in $(seq 200); do grep -q " shell " "$HOME/log" && break; '
                      '/usr/bin/sleep 0.05; done; touch "$HOME/dropped"; exit 1; fi; '
                      'echo "mirror up" >> "$HOME/log"; for _ in $(seq 200); do '
                      'grep -qx "qdbus6 org.kde.kdialog-$(cat "$HOME/n") /ProgressDialog close" "$HOME/log" && break; '
                      '/usr/bin/sleep 0.05; done; echo "mirror closed" >> "$HOME/log"',
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

    def test_failed_connection_offers_another_phone_in_sight(self):
        """The remembered phone refuses (taken once because it was the only one advertising) and
        another is in sight: the dialog offers it, and choosing it starts again with that one,
        without opening Android Mirror again."""
        a, b = ("Phone A", "10.0.0.7", 4100), ("Phone B", "10.0.0.5", 4000)
        code, log, conf = self.run_phone([a, b], conf='PHONE_NAME="Phone A"\n', choose="use:Phone B", extra={
            "adb": 'echo "adb $*" >> "$HOME/log"; case "$1 $2" in "connect 10.0.0.5:4000") echo "connected to $2";; '
                   'connect*) echo "failed to connect to $2";; esac; exit 0'})
        self.assertEqual(code, 0, log)
        self.assertIn("use:Phone B Use Phone B instead", log)
        self.assertNotIn("use:Phone A", log)                       # (not the one that refused)
        self.assertIn("PHONE_NAME=Phone\\ B\n", conf)                 # (remembered, as printf %q writes it)
        self.assertIn("scrcpy -s 10.0.0.5:4000", log)

    def test_its_steps_are_logged_but_never_the_pairing_code(self):
        pairing = "=;wlan0;IPv4;adb-x;_adb-tls-pairing._tcp;local;host.local;10.0.0.5;37001;"
        self.run_phone([("Phone B", "10.0.0.5", 4000)], conf='PHONE_NAME="Phone B"\n', choose="pair", extra={
            "avahi-browse": f'''case "$*" in *pairing*) echo '{pairing}';; *) printf '%s\\n' '{advert("Phone B", "10.0.0.5", 4000)}';; esac''',
            "kdialog": 'case "$*" in *--inputbox*) echo 482913;; *) echo "$CHOOSE";; esac',
            "adb": 'case "$1" in connect) [ -f "$HOME/paired" ] && echo "connected to $2" || echo "failed to connect to $2";; '
                   'pair) read -r c; touch "$HOME/paired"; echo "Successfully paired to $2";; esac; exit 0'})
        plog = Path(self.tmp.name) / "run/phone.log"
        text = plog.read_text()
        self.assertEqual(stat.S_IMODE(plog.stat().st_mode), 0o600)
        for step in ('remembered "Phone B"', "adb connect 10.0.0.5:4000: failed to connect", "after the failed connection: pair",
                     "pairing: the phone offers it at 10.0.0.5:37001", "adb pair 10.0.0.5:37001: Successfully paired",
                     "connected to 10.0.0.5:4000 (adb-PhoneB-a1B2c3): remembered as the phone"):
            self.assertIn(step, text)
        self.assertNotIn("482913", text)

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
            # the first mirror: Reset to defaults, then Restart stream (as phone-touch asks: its
            # request file, then SIGUSR1), and
            # it runs until it's stopped; the restarted one closes
            "scrcpy": 'echo "scrcpy $*" >> "$HOME/log"; [ -f "$HOME/reset" ] && exit 0; touch "$HOME/reset"; '
                      '/usr/bin/sleep 0.5; printf \'PHONE_NAME="Pixel 9"\\n\' > "$HOME/.config/frame-tweaks/phone.conf"; '
                      'touch "$XDG_RUNTIME_DIR/sft-phone.restart"; kill -USR1 "$(cat "$XDG_RUNTIME_DIR/sft-phone.pid")"; exec /usr/bin/sleep 10',
            "sleep": "exec /usr/bin/sleep 0.05"})
        self.assertEqual(code, 0, log)
        runs = [l for l in log.splitlines() if l.startswith("scrcpy ")]
        self.assertEqual(len(runs), 2, log)
        self.assertIn("--video-bit-rate=8M --max-size=1920 --max-fps=90 --no-clipboard-autosync", runs[0])
        self.assertIn("--video-bit-rate=2M --max-size=1024 --max-fps=60 --window-title", runs[1])

    def test_restart_whose_signal_is_lost_still_restarts(self):
        """bash 5.2 can lose the trap of Restart stream's SIGUSR1 (run while it parses a $(...), it
        fails to parse), and the restart did nothing. The request file alone restarts it here (no
        signal at all), at the next check."""
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf='PHONE_NAME="Pixel 9"\nPHONE_MAX_FPS=90\n', extra={
            # (once it's watched: adb shell. Restarted, the mirror closes.)
            "scrcpy": 'echo "scrcpy $*" >> "$HOME/log"; [ -f "$HOME/reset" ] && exit 0; touch "$HOME/reset"; '
                      'for _ in $(seq 200); do grep -q " shell " "$HOME/log" && break; /usr/bin/sleep 0.05; done; '
                      'printf \'PHONE_NAME="Pixel 9"\\n\' > "$HOME/.config/frame-tweaks/phone.conf"; '
                      'touch "$XDG_RUNTIME_DIR/sft-phone.restart"; exec /usr/bin/sleep 20',
            "sleep": "exec /usr/bin/sleep 0.05"})
        self.assertEqual(code, 0, log)
        runs = [l for l in log.splitlines() if l.startswith("scrcpy ")]
        self.assertEqual(len(runs), 2, log)
        self.assertIn("--max-fps=60", runs[1])
        self.assertFalse((Path(self.tmp.name) / "run/sft-phone.restart").exists())   # (done: not again)

    def test_restart_during_the_start_up_check_restarts(self):
        """Restart stream while the first mirror was still being checked (its first 3 s): its trap
        stopped scrcpy, taken then for a mirror that didn't start ("The mirror didn't start", and
        no mirror). The check's sleeps wait here until the restart has been asked for."""
        conf = 'PHONE_NAME="Pixel 9"\nPHONE_MAX_FPS=90\n'
        code, log, _ = self.run_phone([("Pixel 9", "10.0.0.5", 4000)], conf=conf, extra={
            "scrcpy": 'echo "scrcpy $*" >> "$HOME/log"; [ -f "$HOME/reset" ] && exit 0; touch "$HOME/reset"; '
                      'printf \'PHONE_NAME="Pixel 9"\\n\' > "$HOME/.config/frame-tweaks/phone.conf"; '
                      'touch "$XDG_RUNTIME_DIR/sft-phone.restart"; kill -USR1 "$(cat "$XDG_RUNTIME_DIR/sft-phone.pid")"; touch "$HOME/sent"; '
                      'exec /usr/bin/sleep 10',
            "sleep": 'for _ in $(seq 200); do [ -f "$HOME/reset" ] && [ ! -f "$HOME/sent" ] || break; /usr/bin/sleep 0.05; done; '
                     'exec /usr/bin/sleep 0.05'})
        self.assertEqual(code, 0, log)
        self.assertNotIn("didn't start", log)
        runs = [l for l in log.splitlines() if l.startswith("scrcpy ")]
        self.assertEqual(len(runs), 2, log)
        self.assertIn("--max-fps=60", runs[1])

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
    (a minute) whether to keep it on, and with no answer closes the mirror and disconnects. The
    mirror runs until it's stopped.

    Its time is a stand-in clock (date +%s reads $HOME/clock, in ms), moved on only by phone's own
    sleeps: real minutes, decided by its own steps, so a busy test machine slows the test but can't
    change what it sees. (On real seconds, shortened, a stand-in dialog once had a tenth of a
    second to answer, and a mirror's step meant for before the question came after it.) A step a
    stand-in takes at a set time waits for it at $HOME/hold: the clock stops there until the
    stand-in has done it and removed the file."""
    setUp, run_phone = PhonePick.setUp, PhonePick.run_phone
    PHONES = [("Pixel 9", "10.0.0.5", 4000)]
    START = 1_700_000_000_000                    # (the clock's start, ms)
    MIRROR = 'echo "scrcpy $*" >> "$HOME/log"; exec /usr/bin/sleep 120'
    # kdialog --yesno: logged with the time; answers from $HOME/answers (one per ask: yes, no; none
    # left: never answers)
    ASK = ('echo "kdialog $(date +%s.%N) $*" >> "$HOME/log"; a=$(head -1 "$HOME/answers" 2>/dev/null); '
           'sed -i 1d "$HOME/answers" 2>/dev/null; case "$a" in yes) exit 0;; no) exit 1;; esac; exec /usr/bin/sleep 120')
    # sleep N: moves the clock on N s (up to the hold, if any); held, it waits a moment instead.
    # (mv: a reader never sees the file half written)
    SLEEP = ('read -r c < "$HOME/clock"; h=$(cat "$HOME/hold" 2>/dev/null); '
             '[ -n "$h" ] && [ "$c" -ge "$h" ] && exec /usr/bin/sleep 0.02; '
             'case $1 in *.*) i=${1%%.*} f=${1#*.}000;; *) i=$1 f=000;; esac; '
             'n=$((c + 10#${i:-0} * 1000 + 10#${f:0:3})); [ -n "$h" ] && [ "$n" -gt "$h" ] && n=$h; '
             'echo "$n" > "$HOME/clock.new" && mv "$HOME/clock.new" "$HOME/clock"')
    DATE = ('read -r c < "$HOME/clock"; case "$1" in +%s) echo $((c / 1000));; '
            '+%s.%N) printf "%d.%03d000000\\n" $((c / 1000)) $((c % 1000));; *) exec /usr/bin/date "$@";; esac')
    # (in a mirror stand-in: wait, at most 30 s, for the clock to reach the hold)
    AT_HOLD = ('for _ in $(seq 1500); do [ "$(cat "$HOME/clock")" -ge "$(cat "$HOME/hold")" ] && break; '
               '/usr/bin/sleep 0.02; done; ')

    def run_auto(self, conf, answers="", mirror=None, hold=None, adb=None):
        """phone with the stand-in clock, PHONE_MINUTE unset (a minute is 60 s); hold: the clock
        stops at that many seconds in until the mirror stand-in removes $HOME/hold."""
        home = Path(self.tmp.name)
        (home / "answers").write_text(answers)
        (home / "clock").write_text(f"{self.START}\n")
        if hold is not None:
            (home / "hold").write_text(f"{self.START + hold * 1000}\n")
        extra = {"scrcpy": mirror or self.MIRROR, "kdialog": self.ASK, "sleep": self.SLEEP, "date": self.DATE,
                 "notify-send": 'echo "notify $*" >> "$HOME/log"'}
        if adb:
            extra["adb"] = adb
        # (a minute to answer is 120 of its steps: seconds of real time, more on a busy machine)
        return self.run_phone(self.PHONES, conf='PHONE_NAME="Pixel 9"\n' + conf, extra=extra, timeout=120)

    def times(self, log, start):
        """The stand-in clock's times of the lines starting with START, and of the questions."""
        lines = log.splitlines()
        return (float(next(l.split()[1] for l in lines if l.startswith(start))),
                float(next(l.split()[1] for l in lines if "--yesno" in l)))

    def test_no_answer_disconnects(self):
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n")
        self.assertEqual(code, 0, log)
        self.assertEqual(log.count("--yesno"), 1, log)
        self.assertIn("Keep it on", log)
        self.assertIn("Pixel 9 has been mirrored for 1 min.", log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)
        self.assertIn("adb kill-server", log)                        # (no other device on adb: nothing left on)
        # (the minute it was on, then the minute to answer)
        self.assertIn("notify -a Android Mirror Android Mirror disconnected Pixel 9 was mirrored for 2 min", log)
        self.assertNotIn("--title Android Mirror --", log)           # (the mirror window's own title)

    def test_keep_it_on_asks_again_after_the_same_time(self):
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n", answers="yes\n")
        self.assertEqual(log.count("--yesno"), 2, log)
        asked = [float(l.split()[1]) for l in log.splitlines() if "--yesno" in l]
        self.assertGreaterEqual(asked[1] - asked[0], 59.0, log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)

    def test_disconnect_answer_goes_at_once(self):
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n", answers="no\n")
        self.assertEqual(log.count("--yesno"), 1, log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)
        self.assertIn("was mirrored for 1 min", log.split("adb disconnect")[1])   # (not after the minute to answer)

    def test_adbs_server_stays_for_another_device(self):
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n")
        self.assertIn("adb kill-server", log)
        adb = ('echo "adb $*" >> "$HOME/log"; [ "$1" = connect ] && echo "connected to $2"; '
               '[ "$1" = devices ] && printf "List of devices attached\\nemulator-5554\\tdevice\\n"; exit 0')
        (Path(self.tmp.name) / "log").write_text("")
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n", adb=adb)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)
        self.assertNotIn("adb kill-server", log)

    def test_restart_stream_counts_again(self):
        """Restart stream (the gear) starts the time again: asked a full period after it."""
        mirror = ('echo "scrcpy $*" >> "$HOME/log"; if [ ! -f "$HOME/restarted" ]; then touch "$HOME/restarted"; '
                  + self.AT_HOLD + 'echo "restart $(date +%s.%N)" >> "$HOME/log"; rm -f "$HOME/hold"; touch "$XDG_RUNTIME_DIR/sft-phone.restart"; kill -USR1 $PPID; fi; '
                  'exec /usr/bin/sleep 120')
        # (restarted half a minute in: asked a minute after that; without counting again, half a minute after)
        code, log, _ = self.run_auto("PHONE_TIMEOUT=1\n", mirror=mirror, hold=30)
        restarted, asked = self.times(log, "restart ")
        self.assertEqual(log.count("scrcpy -s"), 2, log)
        self.assertGreaterEqual(asked - restarted, 59.0, log)

    def test_never(self):
        """PHONE_TIMEOUT=0: the mirror stays until it's closed (2.5 s here: many minutes on the
        stand-in clock)."""
        code, log, _ = self.run_auto("PHONE_TIMEOUT=0\n", mirror='echo "scrcpy $*" >> "$HOME/log"; /usr/bin/sleep 2.5')
        self.assertEqual(code, 0, log)
        self.assertNotIn("--yesno", log)
        self.assertNotIn("adb disconnect", log)

    def test_a_change_counts_from_then(self):
        """Changed while the mirror is open (the gear, the settings page): it applies to that mirror,
        counted from the change (1 minute set after 2.5 minutes open doesn't disconnect at once)."""
        conf = Path(self.tmp.name) / ".config/frame-tweaks/phone.conf"
        code, log, _ = self.run_auto("PHONE_TIMEOUT=0\n", hold=150, mirror=(
            'echo "scrcpy $*" >> "$HOME/log"; ' + self.AT_HOLD +
            f'echo "changed $(date +%s.%N)" >> "$HOME/log"; echo PHONE_TIMEOUT=1 >> "{conf}"; rm -f "$HOME/hold"; '
            'exec /usr/bin/sleep 120'))
        changed, asked = self.times(log, "changed ")
        self.assertGreaterEqual(asked - changed, 59.0, log)
        self.assertIn("adb disconnect 10.0.0.5:4000", log)

    def test_reset_to_defaults_is_back_to_an_hour(self):
        """Reset to defaults takes PHONE_TIMEOUT out of the file: an hour again, not the value the
        mirror started with (reset half a minute in; the mirror closes after 5 minutes)."""
        conf = Path(self.tmp.name) / ".config/frame-tweaks/phone.conf"
        code, log, _ = self.run_auto("PHONE_TIMEOUT=2\n", hold=30, mirror=(
            'echo "scrcpy $*" >> "$HOME/log"; ' + self.AT_HOLD +
            f'printf \'PHONE_NAME="Pixel 9"\\n\' > "{conf}"; rm -f "$HOME/hold"; '
            f'for _ in $(seq 1500); do [ "$(cat "$HOME/clock")" -ge {self.START + 300_000} ] && break; /usr/bin/sleep 0.02; done'))
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
