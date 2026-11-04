"""The installer window itself, built as it opens, with nothing of this machine's run: its status
checks answered by a stand-in, no update, release, pack or needed.sh checks, no SteamVR buttons,
and its own settings (hidden and folded groups, packs and their trust) in a throwaway folder.
What its list does as packs change under it, how narrow it can be, its error page, closing it."""
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import load_script, untipped_icon_buttons  # noqa: E402  (English, throwaway language files: test_00_english.py)
gui = load_script(ROOT / "gui" / "frame-tweaks-gui.py", "gui")
# The packs' names live in lib/registry.py and lib/userpacks.py (gui.sft.NAME reads them there):
# patched there, a patch reaches the window and sft's own code alike.
import registry  # noqa: E402  (after gui: lib/ is on the path through sft)
import userpacks  # noqa: E402  (after gui: lib/ is on the path through sft)
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402


class WindowTest(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.dir = d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        self.addCleanup(gui.sft.load, refresh=True)          # (the real packs again, once the patches are gone)
        self.statuses, self.errors = {}, []                   # id -> (code, text); others: not installed
        for p in (mock.patch.object(gui, "status", lambda cid: self.statuses.get(cid, (1, ""))),
                  mock.patch.object(gui, "update_check", lambda cid: None),
                  mock.patch.object(gui, "latest_release", lambda url: None),
                  mock.patch.object(gui, "self_update_check", lambda: ""),
                  mock.patch.object(userpacks, "packs_with_updates", lambda: []),
                  mock.patch.object(gui.sft, "apply_formerly", lambda: []),
                  mock.patch.object(gui.sft, "build_version", lambda: "0.0.0"),     # (no git describe)
                  mock.patch.object(gui.sft, "not_needed", lambda rows=None, refresh=False: {}),   # (no needed.sh)
                  mock.patch.multiple(registry, USER_PACKS=d / "packs", CONF=d, TRUSTED=d / "trusted",
                                      OFF_PACKS=d / "off-packs"),
                  mock.patch.object(userpacks, "INSTALLED", d / "state/installed"),
                  mock.patch.multiple(gui.sft, HIDDEN=d / "hidden", SHOWN=d / "shown",
                                      HIDDEN_CATS=d / "hidden-categories", STATE=d / "state"),
                  mock.patch.multiple(gui, HIDDEN_CATS=d / "hidden-categories", COLLAPSED=d / "collapsed"),
                  mock.patch.object(sys, "excepthook", lambda kind, value, tb: self.errors.append(value)),
                  mock.patch.object(gui.Window, "say"),      # (its message's timer would outlive the window)
                  mock.patch.dict(os.environ, {"DISPLAY": "", "FRAME_TWEAKS_PACKS": ""})):
            p.start()
            self.addCleanup(p.stop)
        gui.sft.load(refresh=True)

    def window(self):
        w = gui.Window()
        self.addCleanup(w.deleteLater)
        self.addCleanup(w.close)
        self.settle(w)
        return w

    def settle(self, w):
        """Until what the window started is in (collect, as its timer runs it). (Up to 30 s: a
        busy machine is slow.)"""
        for _ in range(1500):
            if not (w.futures or w.update_futures or w.pack_check or w.self_update or getattr(w, "pack_job", None)
                    or w.updates_timer or w.update_waiting):
                return
            QTest.qWait(20)
        self.fail("still checking")

    def my_pack(self):
        """A pack of mine, trusted: the example's Hello Frame."""
        mine = self.dir / "packs/mine"
        shutil.copytree(ROOT / "examples/hello-pack", mine)
        gui.sft.set_trusted(mine, True)
        gui.sft.load(refresh=True)
        return mine.resolve()

    def ids(self, w):
        return [c["id"] for c in w.rows]

    def test_search_shows_only_the_matches_and_esc_brings_back_the_list(self):
        w = self.window()
        everything = len(w.boxes)
        self.assertTrue(w.search_box.isHidden())
        w.search_button.setChecked(True)
        self.assertFalse(w.search_box.isHidden())
        w.search_box.setText("dictation")
        self.assertIn("dictation", w.boxes)
        self.assertLess(len(w.boxes), everything)
        self.assertTrue(all(gui.matches(next(c for c in w.rows if c["id"] == cid), "dictation") for cid in w.boxes))
        w.search_box.setText("no such tweak anywhere")
        self.assertEqual(w.boxes, {})
        QTest.keyClick(w.search_box, gui.Qt.Key.Key_Escape)
        self.assertFalse(w.search_button.isChecked())
        self.assertTrue(w.search_box.isHidden())
        self.assertEqual(w.search_box.text(), "")
        self.assertEqual(len(w.boxes), everything)

    def test_every_button_without_a_word_has_a_tooltip(self):
        """ⓘ, ⚙, ↻, the search icon and the like: the list, and each page the window opens without
        running anything (Preferences, Packs, a tweak's details, every ⚙ Settings page)."""
        w = self.window()
        pages = {"the list": lambda: None, "Preferences": w.show_prefs, "Packs": w.show_packs,
                 "Details": lambda: w.show_details(w.rows[0])}
        pages.update({f"Settings of {cid}": (lambda c=cid: w.open_settings(c)) for cid in gui.SETTINGS_PAGES})
        self.assertGreater(len(pages), 4)
        for name, show in pages.items():
            with self.subTest(page=name):
                show()
                self.settle(w)
                self.assertEqual(untipped_icon_buttons(w), [])
                w.close_details()
        w.search_button.setChecked(True)               # (the search field and its clear button shown)
        w.search_box.setText("dictation")
        self.assertEqual(untipped_icon_buttons(w), [])
        self.assertEqual(self.errors, [])

    def test_works_on_my_frame_is_with_get_involved(self):
        w = self.window()
        works = [b for b in w.findChildren(QPushButton) if b.text().endswith("Works on my Frame")]
        self.assertEqual(len(works), 1)
        self.assertIsInstance(works[0].parent(), gui.ContributeRow)


class PacksChangeUnderIt(WindowTest):
    """sft read the packs again behind the list's back (the Packs page opening, Check for updates,
    a pack's update ending after Back): the list's rows were the old ones, and checking them raised
    TypeError (the error page, and rows "checking…" for good). The list follows now."""
    def test_packs_opened_after_mine_changed(self):
        mine = self.my_pack()
        w = self.window()
        self.assertIn("hello-frame", self.ids(w))
        readme = mine / "hello-frame/README.md"
        readme.write_text(readme.read_text() + "\nMore.\n")           # (edited: it waits to be trusted again)
        w.show_packs()
        self.settle(w)
        w.go_back()
        w.refresh()
        self.settle(w)
        self.assertNotIn("hello-frame", self.ids(w))
        self.assertNotIn("hello-frame", w.status_labels)
        self.assertEqual(self.errors, [])

    def test_check_for_updates_after_a_pack_was_turned_off(self):
        w = self.window()
        self.assertIn("recline", self.ids(w))
        gui.sft.set_official(gui.sft.THIRD_PARTY, False)                # (./install.sh mods off third-party)
        with mock.patch.object(userpacks, "packs_with_updates", lambda: (gui.sft.load(refresh=True), [])[1]):
            w.update_clicked()                                          # ⟳ Check for updates
            self.settle(w)
        self.assertNotIn("recline", self.ids(w))
        self.assertTrue(w.rows and all(c["id"] in w.state for c in w.rows))
        self.assertEqual(self.errors, [])

    def test_an_update_ending_after_back(self):
        mine = self.my_pack()

        def update_pack(folder):                        # (a git pull that brought a change)
            time.sleep(0.3)
            readme = mine / "hello-frame/README.md"
            readme.write_text(readme.read_text() + "\nNew.\n")
            gui.sft.load(refresh=True)
            return {"files": ["hello-frame/README.md"], "log": ["a change"]}
        origin = lambda folder: "https://example.org/mine.git" if Path(folder) == mine else None   # (added from a link)
        with mock.patch.multiple(userpacks, pack_origin=origin, update_pack=update_pack):
            w = self.window()
            w.pack_updates = {mine}                     # (Check for updates found it newer)
            w.show_pack_updates()
            w.show_packs()
            next(b for b in w.details.findChildren(QPushButton) if b.text() == "Update").click()
            w.go_back()                                 # ← Back while it updates
            self.settle(w)
        self.assertNotIn("hello-frame", self.ids(w))
        self.assertEqual((w.pack_updates, w.pack_update_label.text()), (set(), ""))
        self.assertEqual(self.errors, [])


class TickACategory(WindowTest):
    """The category's two boxes, beside its name: tick or untick every tweak in it that the list
    shows, as clicking each box would (nothing runs until Apply changes)."""

    def buttons(self, w, category):
        head = next(h for h in w.findChildren(gui.CategoryHeader) if category.upper() in
                    h.findChild(QPushButton, "cattoggle").text())
        return head.findChildren(QPushButton, "cattick")

    def test_tick_and_untick_all(self):
        w = self.window()
        cat = next(c["category_en"] for c in w.rows if c["id"] == "arrowpad")
        ids = [c["id"] for c in w.rows if c["category_en"] == cat and c["id"] in w.boxes]
        self.assertGreater(len(ids), 1)
        tick, untick = self.buttons(w, cat)
        tick.click()
        self.assertTrue(all(w.boxes[i].isChecked() for i in ids))
        self.assertEqual(sorted(w.pending_changes()[0]), sorted(ids))          # (none installed here)
        self.assertTrue(w.apply_button.isEnabled())
        others = [c["id"] for c in w.rows if c["category_en"] != cat and c["id"] in w.boxes]
        self.assertFalse(any(w.boxes[i].isChecked() for i in others))          # (its own only)
        untick.click()
        self.assertFalse(any(w.boxes[i].isChecked() for i in ids))
        self.assertEqual(w.pending_changes(), ([], []))

    def test_a_folded_category_and_hidden_rows(self):
        w = self.window()
        cat = next(c["category_en"] for c in w.rows if c["id"] == "arrowpad")
        w.toggle_collapsed(cat)
        self.settle(w)
        self.assertNotIn("arrowpad", w.boxes)
        self.buttons(w, cat)[0].click()
        self.assertIn("arrowpad", w.pending_changes()[0])                     # (wanted, without a box)
        with mock.patch.object(w, "hidden", lambda: {"arrowpad"}):
            w.wanted.clear()
            w.tick_category(cat, True)
            self.assertNotIn("arrowpad", w.wanted)                            # (hidden: not shown, not ticked)
        with mock.patch.object(gui.sft, "not_needed", lambda rows=None, refresh=False: {"arrowpad": "no"}):
            w.wanted.clear()
            w.tick_category(cat, True)
            self.assertNotIn("arrowpad", w.wanted)                            # (not needed: not offered)


class Narrowest(WindowTest):
    def test_every_rows_buttons_at_the_narrowest(self):
        """The list doesn't scroll sideways: at its narrowest the window still fits every row's
        buttons, whole. (It could be made narrower than its rows, which cut off Hide, ↻, ⓘ and Run.)
        The widest case: every row waiting for a SteamVR restart (⟳ Restart SteamVR), hidden ones
        shown (Unhide), a page of its own ("🔑 Wallet apps")."""
        self.statuses.update({c["id"]: (gui.RESTART, "waiting for a SteamVR restart") for c in gui.sft.components()})
        w = self.window()
        w.show_hidden.setChecked(True)
        w.show()
        w.resize(1, 760)
        QTest.qWait(100)
        view = w.scroll.viewport()
        self.assertEqual(w.width(), w.minimumWidth())
        self.assertGreater(len(w.row_widgets), 20)
        for row in w.row_widgets:
            for b in row.findChildren(QPushButton):
                if b.isVisibleTo(row):
                    right = b.mapTo(view, b.rect().topRight()).x()
                    self.assertLessEqual(right, view.width(), (getattr(row, "comp", {}).get("id"), b.text()))
                    self.assertGreaterEqual(b.width(), b.sizeHint().width(), b.text())


class Closing(WindowTest):
    def test_closing_while_it_checks(self):
        """Closing cancels the checks still waiting, and the window stops looking at them: it raised
        CancelledError for each (into window.log)."""
        self.statuses = {}
        with mock.patch.object(gui, "status", lambda cid: (time.sleep(0.1), (1, ""))[1]):
            w = gui.Window()
            self.addCleanup(w.deleteLater)
            w.show()
            for _ in range(500):                # (until its checks have started: later on a busy machine)
                if w.futures:
                    break
                QTest.qWait(20)
            self.assertTrue(w.futures)
            w.close()
            self.assertFalse(w.collector.isActive())
            QTest.qWait(300)
            w.collect()
        self.assertEqual(self.errors, [])


class ErrorPage(WindowTest):
    def test_back_closes_the_page_that_was_open(self):
        """(it went back to the list with that page still in the window: its language then never
        followed the keyboard's, since a page was open)"""
        w = self.window()
        w.show_readme()
        page = w.details
        with mock.patch.object(gui.sys, "__excepthook__"):
            w.show_error(TypeError, TypeError("something"), None)
        self.assertIs(w.stack.currentWidget(), w.error_page)
        next(b for b in w.error_page.findChildren(QPushButton) if b.text() == "← Back").click()
        self.assertIsNone(w.details)
        self.assertEqual(w.stack.indexOf(page), -1)
        self.assertEqual(w.stack.currentIndex(), 0)


if __name__ == "__main__":
    unittest.main()


class SymbolFonts(unittest.TestCase):
    """ⓘ and ⚙ came out squeezed sideways after SteamOS 0.5.7's beta: the window's font has no such
    glyphs, and fontconfig filled them from Adwaita Mono, a monospace font. Noto's symbol fonts
    come right after the window's own now."""

    def test_the_symbol_fonts_follow_the_windows_font(self):
        app = QApplication.instance() or QApplication([])
        before = app.font()
        self.addCleanup(app.setFont, before)
        gui._symbol_fonts(app)
        fams = app.font().families()
        self.assertEqual(fams[0], before.families()[0] if before.families() else before.family())
        self.assertEqual(fams[-2:], ["Noto Sans Symbols", "Noto Sans Symbols 2"])
        gui._symbol_fonts(app)                                  # (twice: no duplicates)
        self.assertEqual(app.font().families().count("Noto Sans Symbols"), 1)
