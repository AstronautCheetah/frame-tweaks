"""lib/browser.py: which session a program is in, where a link goes, and how the default
browser's processes are recognised (Flatpak id, or its program behind wrappers)."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import browser  # noqa: E402
from browser import DESKTOP, VR  # noqa: E402


class Sessions(unittest.TestCase):
    def test_session_of(self):
        self.assertEqual(browser.session_of({"XDG_CURRENT_DESKTOP": "gamescope", "DISPLAY": ":0"}), VR)
        self.assertEqual(browser.session_of({"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0"}), DESKTOP)
        self.assertEqual(browser.session_of({"WAYLAND_DISPLAY": "/run/flatpak/wayland-0"}), DESKTOP)
        self.assertEqual(browser.session_of({"DISPLAY": ":0"}), VR)
        self.assertIsNone(browser.session_of({}))

    def test_choose(self):
        self.assertEqual(browser.choose(VR, {VR, DESKTOP}), VR)          # ours first
        self.assertEqual(browser.choose(DESKTOP, {VR, DESKTOP}), DESKTOP)
        self.assertEqual(browser.choose(VR, {DESKTOP}), DESKTOP)         # where it's running
        self.assertEqual(browser.choose(DESKTOP, {VR}), VR)
        self.assertEqual(browser.choose(DESKTOP, set()), VR)             # not running: VR

    def test_matcher(self):
        flat = browser.matcher({"X-Flatpak": "org.mozilla.firefox", "Exec": "x"})
        self.assertTrue(flat(1, {"FLATPAK_ID": "org.mozilla.firefox"}))
        self.assertFalse(flat(1, {}))
        native = browser.matcher({"Exec": "/home/u/.local/bin/wallet-gate env A=1 /usr/bin/chromium %U"})
        with mock.patch.object(browser, "proc_cmd", return_value=["/usr/lib/chromium/chromium", "--type=x"]):
            self.assertTrue(native(1, {}))
        with mock.patch.object(browser, "proc_cmd", return_value=["/usr/bin/konsole"]):
            self.assertFalse(native(1, {}))
        with mock.patch.object(browser, "proc_cmd", side_effect=[["/usr/bin/chromium"], []]):
            self.assertTrue(native(1, {}))       # (read once: a process that ends meanwhile is no IndexError)

    def test_default_app_asks_as_desktop_mode_first(self):
        """The VR session doesn't read KDE's defaults (a folder would open in Kate there)."""
        def fake(*args, env=None):
            if args[:2] == ("query", "default") and args[2] == "inode/directory":
                return "org.kde.dolphin.desktop" if env and env.get("XDG_CURRENT_DESKTOP") == "KDE" else "org.kde.kate.desktop"
            return ""
        with mock.patch.object(browser, "xdg_mime", side_effect=fake):
            self.assertEqual(browser.target_app(str(Path(__file__).parent)), "org.kde.dolphin.desktop")
            self.assertEqual(browser.target_app("file://" + str(Path(__file__).parent)), "org.kde.dolphin.desktop")

    def test_web_links_go_to_the_browser(self):
        with mock.patch.object(browser, "default_browser", return_value="b.desktop"), \
                mock.patch.object(browser, "usable", return_value=True):
            self.assertEqual(browser.target_app("https://example.com/x"), "b.desktop")

    def test_session_env_takes_the_display_keys(self):
        ref = {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":2", "OTHER": "x",
               "XDG_RUNTIME_DIR": "/run/user/1000/nested_plasma", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/tmp/d"}
        own = {"XDG_CURRENT_DESKTOP": "gamescope", "DISPLAY": ":0", "XDG_DESKTOP_PORTAL_DIR": "/g", "HOME": "/h",
               "XDG_RUNTIME_DIR": "/run/user/1000", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}
        with mock.patch.dict(os.environ, own, clear=True), mock.patch.object(browser, "pids", return_value=[7]), \
                mock.patch.object(browser, "proc_cmd", return_value=["/usr/bin/plasmashell"]), \
                mock.patch.object(browser, "proc_env", return_value=ref):
            env = browser.session_env(DESKTOP)
        # Desktop mode's own runtime folder and bus too: Firefox finds its running copy there.
        self.assertEqual(env, {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":2", "HOME": "/h",
                               "XDG_RUNTIME_DIR": "/run/user/1000/nested_plasma",
                               "DBUS_SESSION_BUS_ADDRESS": "unix:path=/tmp/d"})



class DefaultBrowser(unittest.TestCase):
    """Any browser, not only Firefox: the default one, unless it isn't one (SteamOS's "Install
    Chromium" placeholder, which only opens the software store, or an uninstalled app); then an
    installed one, a running one first, and the note says how to set a default."""
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = Path(self.tmp.name)
        self.apps = d / "share/applications"
        self.apps.mkdir(parents=True)
        bin_ = d / "bin"
        bin_.mkdir()
        for name in ("brave", "chromium"):
            (bin_ / name).write_text("#!/bin/sh\n")
            (bin_ / name).chmod(0o755)
        self.entry("org.chromium.Chromium.desktop", "Install Chromium",
                   "sh -c 'xdg-open appstream://org.chromium.Chromium' %U")
        self.entry("com.brave.Browser.desktop", "Brave", f"{bin_}/brave %U")
        self.entry("chromium.desktop", "Chromium", "chromium %U")
        self.entry("gone.desktop", "Gone", "/no/such/browser %U")
        (self.apps / "mimeinfo.cache").write_text(
            "[MIME Cache]\nx-scheme-handler/https=org.chromium.Chromium.desktop;gone.desktop;chromium.desktop;com.brave.Browser.desktop;\n")
        env = {"XDG_DATA_HOME": str(d / "share"), "XDG_DATA_DIRS": str(d / "none"),
               "PATH": f"{bin_}:/usr/bin:/bin", "HOME": str(d)}
        for p in (mock.patch.dict(os.environ, env),
                  mock.patch.object(browser, "data_dirs", lambda: [str(d / "share")])):   # (not this machine's Flatpaks)
            p.start()
            self.addCleanup(p.stop)

    def entry(self, app, name, cmd):
        (self.apps / app).write_text(f"[Desktop Entry]\nType=Application\nName={name}\nExec={cmd}\n"
                                     "MimeType=x-scheme-handler/http;x-scheme-handler/https;\n")

    def test_usable(self):
        self.assertFalse(browser.usable("org.chromium.Chromium.desktop"))      # (the store placeholder)
        self.assertFalse(browser.usable("gone.desktop"))
        self.assertFalse(browser.usable("not-there.desktop"))
        self.assertTrue(browser.usable("com.brave.Browser.desktop"))
        self.assertTrue(browser.usable("chromium.desktop"))
        self.assertEqual(browser.installed_browsers(), ["chromium.desktop", "com.brave.Browser.desktop"])

    def test_a_broken_entry_is_left_out(self):
        """A desktop entry that links to an app since removed, or one that can't be read, is left out:
        the first raised FileNotFoundError, and then no web link opened at all."""
        (self.apps / "aaa-gone.desktop").symlink_to(self.apps / "nowhere" / "gone.desktop")
        locked = self.apps / "locked.desktop"
        locked.write_text("[Desktop Entry]\nName=Locked\n")
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o644)
        with open(self.apps / "mimeinfo.cache", "a") as f:
            f.write("x-scheme-handler/https=locked.desktop;aaa-gone.desktop;\n")
        self.assertEqual(browser.installed_browsers(), ["chromium.desktop", "com.brave.Browser.desktop"])
        with mock.patch.object(browser, "default_browser", return_value=None), \
                mock.patch.object(browser, "running_sessions", return_value=set()):
            self.assertEqual(browser.browser_choice(), ("chromium.desktop", ""))

    def test_any_default_browser_is_used(self):
        with mock.patch.object(browser, "default_browser", return_value="com.brave.Browser.desktop"):
            self.assertEqual(browser.browser_choice(), ("com.brave.Browser.desktop", None))

    def test_a_placeholder_default_gives_way_to_a_running_browser(self):
        with mock.patch.object(browser, "default_browser", return_value="org.chromium.Chromium.desktop"), \
                mock.patch.object(browser, "running_sessions",
                                  side_effect=lambda a: {VR} if a == "com.brave.Browser.desktop" else set()):
            self.assertEqual(browser.browser_choice(), ("com.brave.Browser.desktop", "org.chromium.Chromium.desktop"))
        with mock.patch.object(browser, "default_browser", return_value=None), \
                mock.patch.object(browser, "running_sessions", return_value=set()):
            self.assertEqual(browser.browser_choice(), ("chromium.desktop", ""))     # (none set: the system's order)

    def test_the_note_says_how_to_set_one(self):
        with mock.patch.object(browser, "default_browser", return_value="org.chromium.Chromium.desktop"), \
                mock.patch.object(browser, "running_sessions", return_value=set()), \
                mock.patch.object(browser, "session_env", return_value=dict(os.environ)), \
                mock.patch.object(browser.subprocess, "Popen") as popen, mock.patch.object(browser, "log"):
            browser.STOOD_IN.clear()
            note, proc, _h = browser.launch("https://example.com")
        self.assertEqual(popen.call_args.args[0], ["gtk-launch", "chromium.desktop", "https://example.com"])
        self.assertIn("Opened in Chromium", note)
        self.assertIn("Your default browser, Install Chromium, can't open links, so Chromium did", proc.warning)
        self.assertIn("Default Applications", proc.warning)

    def test_a_shell_wrapped_command_isnt_taken_for_every_shell(self):
        test = browser.matcher({"Exec": "sh -c 'xdg-open appstream://x' %U"})
        with mock.patch.object(browser, "proc_cmd", return_value=["/usr/bin/sh", "-c", "anything"]):
            self.assertFalse(test(1, {}))


if __name__ == "__main__":
    unittest.main()


def until_visible(p, url, timeout=10):
    """Wait for a just-started process to show the link on its command line (a busy machine, CI's
    runner say, can take a moment): what still_stuck looks for."""
    import time
    end = time.monotonic() + timeout
    while time.monotonic() < end and not any(url in browser.proc_cmd(pid) for pid in [p.pid]):
        time.sleep(0.05)


class StuckHandoff(unittest.TestCase):
    def test_a_launch_that_never_handed_off_is_stopped(self):
        """A browser launch still holding the link after the hand-off time is stuck ("already
        running, but is not responding"): it's stopped, and the window puts the link on the
        clipboard instead."""
        import subprocess, sys
        url = "https://example.com/stuck-test?x=1&y=2"
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", url])
        self.addCleanup(lambda: p.poll() is None and p.kill())
        until_visible(p, url)
        with mock.patch.object(browser, "log", lambda msg: None):
            self.assertTrue(browser.still_stuck(None, url))
            p.wait(timeout=5)
            self.assertFalse(browser.still_stuck(None, url))      # (nothing left: it handed off)

    def test_the_browser_this_link_started_is_left_alone(self):
        """A first click on a link started the browser with it on its command line; after a second
        click on it, only the second launch's processes can be the stuck ones."""
        import subprocess, sys
        url = "https://example.com/stuck-test?x=3"
        started = lambda: subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", url])
        first = started()
        self.addCleanup(lambda: first.poll() is None and first.kill())
        until_visible(first, url)
        with mock.patch.object(browser, "plan", return_value=("b.desktop", VR, {})), \
                mock.patch.object(browser, "running_sessions", return_value={VR}), \
                mock.patch.object(browser.subprocess, "Popen") as popen, \
                mock.patch.object(browser, "browser_name", return_value="B"), \
                mock.patch.object(browser, "log", lambda msg: None):
            _note, proc, handoff = browser.launch(url)            # (nothing is started: Popen is a stand-in)
        self.assertTrue(handoff)
        self.assertEqual(popen.call_args[0][0], ["gtk-launch", "b.desktop", url])
        self.assertIn(first.pid, proc.had_link)
        second = started()
        self.addCleanup(lambda: second.poll() is None and second.kill())
        until_visible(second, url)
        with mock.patch.object(browser, "log", lambda msg: None):
            self.assertTrue(browser.still_stuck(proc, url))
        second.wait(timeout=5)
        self.assertIsNone(first.poll())
