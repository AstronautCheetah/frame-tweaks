"""Memory limits, VR memory guard's page in the installer window: it shows what
vr-memory-guard-tool says (the installed Flatpak apps, each with its own limit or shared, and the
memory kept for VR), steps in half GBs within what the tool allows, keeps Apply dimmed until
something changes, and runs the tool's commands for what changed (the reserve first, then apply).
A stand-in tool answers for the real one."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# (as test_00_english.py does, for when this file runs alone: English, and the language the window
# announces as it's imported kept from the real programs, which would follow it)
_ANNOUNCED, _PREFERRED = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()   # (removed at the end)
for k, v in {"FRAME_TWEAKS_LANGUAGE": "en", "FRAME_TWEAKS_KEYBOARD": "0",
             "FRAME_TWEAKS_ANNOUNCE_FILE": os.path.join(_ANNOUNCED.name, "language"),
             "FRAME_TWEAKS_PREFERENCE_FILE": os.path.join(_PREFERRED.name, "language")}.items():
    os.environ.setdefault(k, v)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script  # noqa: E402
gui = load_script(ROOT / "gui" / "frame-tweaks-gui.py", "gui")
import memory_page as mp  # noqa: E402  (the window's Memory limits page; gui put it on sys.path)
from PyQt6.QtWidgets import QApplication, QLabel, QWidget  # noqa: E402

# (what the real tool's info says on a Frame with 5G kept for VR: see tests/test_vr_memory_guard.py)
INFO = {"total": 15662, "reserve": 5120, "apps_swap": 2048, "pool": 10542, "min_reserve": 1024,
        "max_reserve": 13614, "min_limit": 256, "default_swap": 1024,
        "apps": [{"id": "org.mozilla.firefox", "limit": 5120, "swap": 1024, "installed": True},
                 {"id": "org.signal.Signal", "limit": None, "swap": None, "installed": True},
                 {"id": "org.gone.App", "limit": 3072, "swap": 1024, "installed": False}]}


class Window(QWidget):
    def go_back(self):
        pass


class Steps(unittest.TestCase):
    def test_steps_sizes_and_texts(self):
        self.assertEqual(mp.step(5120, 1, 512, 10542), 5632)
        self.assertEqual(mp.step(3500, 1, 512, 10542), 3584)          # (a value from the file: to its neighbour)
        self.assertEqual(mp.step(3500, -1, 512, 10542), 3072)
        self.assertEqual(mp.step(10240, 1, 512, 10542), 10542)         # (no further than the pool)
        self.assertEqual(mp.step(512, -1, 512, 10542), 512)
        self.assertEqual([mp.size_arg(5120), mp.size_arg(2560), mp.size_arg(10542)], ["5G", "2560M", "10542M"])
        self.assertEqual([mp.gb_text(5120), mp.gb_text(2560), mp.gb_text(3500)], ["5 GB", "2.5 GB", "3.42 GB"])


class Page(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t, True)
        self.t, self.log = t, t / "asked"
        (t / "info.json").write_text(json.dumps(INFO))
        self.tool = t / "vr-memory-guard-tool"
        self.tool.write_text(f'#!/bin/bash\necho "$*" >> {self.log}\ncase "$1" in\n'
                             f'  info) cat {t}/info.json ;;\n'
                             '  set) [ "$2" = org.signal.Signal ] && [ -e "${0%/*}/refuse" ] && { echo "nope" >&2; exit 1; }'
                             '; echo "saved $2" ;;\n'
                             '  apply) printf "Flatpak apps together: up to 10030 MB.\\nWith a limit of their own: x.\\n" ;;\n'
                             'esac\n')
        self.tool.chmod(0o755)
        (t / "apps").mkdir()
        (t / "apps/org.mozilla.firefox.desktop").write_text("[Desktop Entry]\nName=Firefox\nIcon=org.mozilla.firefox\n")
        for p in (mock.patch.object(mp, "TOOL", self.tool), mock.patch.object(mp, "FLATPAK_APPS", [t / "apps"]),
                  mock.patch.dict(os.environ, {"FRAME_TWEAKS_DRY_RUN": "1"})):
            p.start()
            self.addCleanup(p.stop)

    def page(self):
        return mp.MemoryLimits(Window())

    def test_shows_the_installed_apps_and_apply_is_dimmed(self):
        page = self.page()
        self.assertEqual(set(page.controls), {"org.mozilla.firefox", "org.signal.Signal"})    # (not org.gone.App)
        own, stepper, _note = page.controls["org.mozilla.firefox"]
        self.assertTrue(own.isChecked())
        self.assertIn("5 GB", stepper.value.text())
        own, stepper, _note = page.controls["org.signal.Signal"]
        self.assertFalse(own.isChecked())
        self.assertEqual(stepper.value.text(), "shared")
        self.assertFalse(stepper.more.isEnabled())
        self.assertIn("5 GB", page.reserve.value.text())
        self.assertIn("10.29 GB", page.pool.text())                    # (10542 MB)
        self.assertTrue(any(lab.text().startswith("<b>Firefox</b>") for lab in page.findChildren(QLabel)))
        self.assertEqual(page.apply.objectName(), "apply")
        self.assertFalse(page.apply.isEnabled())
        self.assertGreaterEqual(page.controls["org.mozilla.firefox"][1].more.minimumWidth(), 52)   # (a laser's target)

    def test_changes_light_apply_which_runs_them_reserve_first_then_dims(self):
        page = self.page()
        page.controls["org.mozilla.firefox"][1].more.click()            # 5 → 5.5 GB
        self.assertTrue(page.apply.isEnabled())
        page.controls["org.signal.Signal"][0].click()                   # Own limit: from 4 GB
        self.assertIn("4 GB", page.controls["org.signal.Signal"][1].value.text())
        page.reserve.more.click()                                       # 5 → 5.5 GB for VR
        with contextlib.redirect_stdout(io.StringIO()) as out:
            page.apply.click()
        self.assertEqual(out.getvalue().splitlines(), [
            "would run: vr-memory-guard-tool reserve 5632M",
            "would run: vr-memory-guard-tool set org.mozilla.firefox 5632M",
            "would run: vr-memory-guard-tool set org.signal.Signal 4G",
            "would run: vr-memory-guard-tool apply"])
        self.assertFalse(page.apply.isEnabled())

    def test_unticking_makes_it_shared_and_ticking_again_brings_back_what_was_saved(self):
        page = self.page()
        own = page.controls["org.mozilla.firefox"][0]
        own.click()
        self.assertEqual(page.commands(), [["set", "org.mozilla.firefox", "shared"]])
        self.assertFalse(page.controls["org.mozilla.firefox"][1].less.isEnabled())
        own.click()
        self.assertEqual(page.commands(), [])
        self.assertFalse(page.apply.isEnabled())

    def test_more_for_vr_never_leaves_a_limit_above_the_apps_pool(self):
        page = self.page()
        for _i in range(40):
            page.reserve.more.click()
        self.assertEqual(page.chosen["reserve"], 13614)                 # (the tool's max_reserve: 2 GB left)
        self.assertFalse(page.reserve.more.isEnabled())
        self.assertEqual(page.chosen["apps"]["org.mozilla.firefox"], 2048)
        self.assertFalse(page.controls["org.mozilla.firefox"][1].more.isEnabled())
        for _i in range(40):
            page.reserve.less.click()
        self.assertEqual(page.chosen["reserve"], 1024)
        self.assertFalse(page.reserve.less.isEnabled())

    def test_apply_runs_the_tool_then_reads_it_again_and_says_what_failed(self):
        os.environ.pop("FRAME_TWEAKS_DRY_RUN")
        page = self.page()
        page.controls["org.mozilla.firefox"][1].less.click()
        page.apply.click()
        asked = self.log.read_text().splitlines()
        self.assertEqual(asked, ["info", "set org.mozilla.firefox 4608M", "apply", "info"])
        self.assertIn("With a limit of their own", page.notice.text())
        self.assertFalse(page.apply.isEnabled())                        # (what the tool says now is what's saved)
        (self.t / "refuse").touch()
        page.controls["org.signal.Signal"][0].click()
        page.apply.click()
        self.assertIn("Didn't work: nope", page.notice.text())
        self.assertNotIn("apply", self.log.read_text().splitlines()[-2:])  # (stopped at the first that failed)

    def test_without_the_tool_it_says_to_reinstall(self):
        self.tool.unlink()
        page = self.page()
        self.assertIn("reinstall", page.notice.text())
        self.assertFalse(page.apply.isEnabled())
        self.assertEqual(page.controls, {})

    def test_the_tweaks_row_opens_it(self):
        label, page, tip = gui.PAGES["vr-memory-guard"]
        self.assertIs(page, mp.MemoryLimits)
        self.assertIn("Memory limits", label)
        self.assertTrue(tip)
        self.assertEqual(len(gui.PAGES["wallet"]), 3)


if __name__ == "__main__":
    unittest.main()
