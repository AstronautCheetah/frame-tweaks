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
        with mock.patch.object(browser, "default_browser", return_value="b.desktop"):
            self.assertEqual(browser.target_app("https://example.com/x"), "b.desktop")

    def test_session_env_takes_the_display_keys(self):
        ref = {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":2", "OTHER": "x"}
        own = {"XDG_CURRENT_DESKTOP": "gamescope", "DISPLAY": ":0", "XDG_DESKTOP_PORTAL_DIR": "/g", "HOME": "/h"}
        with mock.patch.dict(os.environ, own, clear=True), mock.patch.object(browser, "pids", return_value=[7]), \
                mock.patch.object(browser, "proc_cmd", return_value=["/usr/bin/plasmashell"]), \
                mock.patch.object(browser, "proc_env", return_value=ref):
            env = browser.session_env(DESKTOP)
        self.assertEqual(env, {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":2", "HOME": "/h"})


if __name__ == "__main__":
    unittest.main()
