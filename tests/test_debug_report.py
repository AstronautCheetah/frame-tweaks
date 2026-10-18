"""./install.sh debug-info's report, from a log of an earlier run with every kind of name, address,
token and key it removes in it: each is replaced, its first line lists exactly those, and what
only looks like one stays (std::string, the service type _adb-tls-connect._tcp, adb-scrcpy-update,
a commit, a time). Each is replaced whole, also where it holds the user name, or follows a _ or a
letter. Of the settings file from before 0.6, only its PHONE_NAME line is read: it may be another
program's. (Dash-separated MACs, GitHub tokens, 64-hex tokens, WireGuard keys, adb's names for
phones and a phone remembered before 0.6 went through, while `std::string` became
`st<ipv6>string`.) The token- and key-shaped samples are made as the test runs. In a throwaway
home with every official pack turned off; systemctl, hostname and git are stand-ins (nothing
reaches the session, and the checkout's git isn't asked)."""
import base64
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import sandbox_env, stub  # noqa: E402


class DebugReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.home, self.stubs = t / "home", t / "stubs"
        (self.home / ".config/frame-tweaks/installer").mkdir(parents=True)
        (self.home / ".config/frame-tweaks/installer/off-packs").write_text("core\nintegrations\nthird-party\n")
        stub(self.stubs, "systemctl", "exit 0")
        stub(self.stubs, "hostname", "echo frame-bob")
        stub(self.stubs, "git", "exit 128")                  # (the version: VERSION's)
        self.logs = self.home / ".local/state/frame-tweaks/logs"
        self.logs.mkdir(parents=True)

    def report(self, log, user="alice"):
        (self.logs / "20260101-000000-1-install.log").write_text(log)
        r = subprocess.run([str(ROOT / "install.sh"), "debug-info"], env=sandbox_env(self.home, self.stubs, USER=user),
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return Path(re.search(r"^Wrote (.+)$", r.stdout, re.M)[1]).read_text()

    def test_names_addresses_tokens_and_keys_removed(self):
        phone, old_phone = "Galaxy S24+ (Bob)", "alice's Pixel 9"      # (+ and ( ) mean something to sed -E)
        ran = self.home / "ran"
        (self.home / ".config/frame-tweaks/phone.conf").write_text(f"PHONE_TOUCH=1\nPHONE_NAME={shlex.quote(phone)}\n")
        (self.home / ".config/phone.conf").write_text(                                  # (before 0.6)
            f"PHONE_NAME={shlex.quote(old_phone)}\ntouch {shlex.quote(str(ran))}\n")
        letters = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"                 # (36: a classic token's length)
        tokens = [f"gh{kind}_{letters}" for kind in "opusr"] + ["github_pat_" + "11ABCDEFG0" * 2 + "_" + letters * 2]
        hex64 = "0123456789abcdef" * 4
        keys = [base64.b64encode(bytes(range(32))).decode(), base64.b64encode(bytes([0xfb, 0xff] * 16)).decode()]
        keys.append("/alice/" + "Ab0+" * 9 + "=")                         # (the user name in it, between / /)
        mac_dashes = "-".join(["AA", "BB", "CC", "DD", "EE", "0F"])
        adb_name = "adb-" + "R5CT1234ABC" + "-" + "AbCdEf"
        lines = {      # what's written: what the report must say instead
            f"Connecting to {phone}…": "Connecting to <phone>…",
            f"Several are advertising: {phone}, {old_phone}": "Several are advertising: <phone>, <phone>",
            f"{adb_name}._adb-tls-connect._tcp 192.168.1.23:37011": "<phone>._adb-tls-connect._tcp <ip>:37011",
            f"alice@frame-bob:{self.home}/x$ adb connect 10.0.0.7:5555": "<user>@<host>:~/x$ adb connect <ip>:5555",
            f"gh auth: {tokens[0]} {tokens[1]}, {tokens[2]}": "gh auth: <token> <token>, <token>",
            f"x-access-token:{tokens[3]}@github.com {tokens[4]}": "x-access-token:<token>@github.com <token>",
            f"fine-grained: {tokens[5]}": "fine-grained: <token>",
            f"nordvpn token={hex64}": "nordvpn token=<token>",
            f"env MY_{tokens[0]} nord_{hex64}, %3D{tokens[1]}": "env MY_<token> nord_<token>, %3D<token>",
            f"wg: {keys[2]}": "wg: <key>",
            f"PrivateKey = {keys[0]}": "PrivateKey = <key>",
            f'"key": "{keys[1]}" {keys[0]}': '"key": "<key>" <key>',
            f"bluetooth aa:bb:cc:dd:ee:0f, wifi {mac_dashes}, mail bob.smith@example.com":
                "bluetooth <mac>, wifi <mac>, mail <email>",
            "inet6 fe80::1c2b:3aff:fe4d:5e6f%wlan0 ::1 [2001:db8::1]:8080 2001:db8:0:0:1:0:0:1 fe80::/64":
                "inet6 <ipv6>%wlan0 <ipv6> [<ipv6>]:8080 <ipv6> <ipv6>/64",
            # (only look like them: kept)
            "terminate called after throwing an instance of 'std::string' in std::vector<int>::at()":
                "terminate called after throwing an instance of 'std::string' in std::vector<int>::at()",
            "adb-scrcpy: _adb-tls-connect._tcp and _adb-tls-pairing._tcp at 12:34:56":
                "adb-scrcpy: _adb-tls-connect._tcp and _adb-tls-pairing._tcp at 12:34:56",
            "adb-scrcpy-update: done": "adb-scrcpy-update: done",
            "commit 0123456789abcdef0123456789abcdef01234567, version 2.42304.0, ydotool 1.0.4-2":
                "commit 0123456789abcdef0123456789abcdef01234567, version 2.42304.0, ydotool 1.0.4-2",
        }
        report = self.report("\n".join(lines) + "\n")
        for written, said in lines.items():
            self.assertIn(said + "\n", report, written)
        for secret in (phone, old_phone, adb_name, *tokens, hex64, *keys, mac_dashes, "frame-bob", str(self.home),
                       "alice", "Pixel", "Ab0+", "192.168", "example.com", "fe80::1c2b", "2001:db8"):
            self.assertNotIn(secret, report)
        self.assertFalse(ran.exists())
        first = report.splitlines()[0]
        for what in ("your user name", "home folder path", "host name", "phone names Android Mirror remembers",
                     "adb's names for phones", "IP, MAC and e-mail addresses", "GitHub tokens",
                     "64 hex digits, or as 44 base64 characters ending in =", "Nothing else is."):
            self.assertIn(what, first)

    def test_steamos_only_where_it_names_you(self):
        """The Frame's user is steamos: the name goes where it's the user's, not from SteamOS's own names."""
        report = self.report("steamos-manager[812]: started; /usr/lib/steamos/x\nsteamos@frame-bob:~$ id\n"
                             "uid=1000(steamos) gid=1000(steamos)\n/home/steamos/x\n", user="steamos")
        for line in ("steamos-manager[812]: started; /usr/lib/steamos/x", "<user>@<host>:~$ id",
                     "uid=1000(<user>) gid=1000(<user>)", "/home/<user>/x"):
            self.assertIn(line + "\n", report)


if __name__ == "__main__":
    unittest.main()
