#!/usr/bin/env python3
"""Frame Tweaks: graphical installer.

Rows grouped by category (convenience first, developer tools last). Tick to install, untick
to remove; click a row for details (what it is, why it's here, who made it, its README).
Rows can be hidden (never removed); some start hidden, like whisper-frame while its window mic
costs VR performance. Status checks run in the background so the window never freezes.
Changes run in a Konsole window via ./install.sh. Styled after Full Keyboard's Graphite theme.
"""
import html
import os
import re
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt6.QtCore import QEvent, QProcess, Qt, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QStackedWidget, QTextBrowser, QVBoxLayout, QWidget)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))
os.environ.setdefault("FRAME_TWEAKS_LIB", str(REPO / "lib"))   # (packs' scripts source the helpers through it)
sys.path.insert(0, str(REPO / "gui"))           # (its pages, e.g. wallet_page.py)
import sft  # noqa: E402  (shared with ./install.sh: components, hidden rows, settings)
from sft import COLLAPSED, HIDDEN_CATS, component, components, current_release, run_label, write_set  # noqa: E402
import browser  # noqa: E402  (web links, across the VR and desktop sessions)
import i18n  # noqa: E402
from i18n import _, N_, ngettext  # noqa: E402  (translations: locale/README.md)
# The window follows the keyboard itself (not the language ./install.sh found when it started it),
# and whatever it runs (status checks, installs, Run) gets the window's language.
i18n.INHERIT = False
i18n.CATALOGUE = i18n.Catalogue()
sft.load(refresh=True)                    # (sft read the tweaks' text on import, maybe in the
sft.SETTINGS = sft.settings_specs()       # language this window was started with: again, in ours)


def pass_language():
    """What the window runs gets its language; running programs (Arrow Pad, Screen snip) hear of it."""
    os.environ["FRAME_TWEAKS_LANG_RESOLVED"] = i18n.CATALOGUE.language or "en"
    i18n.announce(i18n.CATALOGUE.language)


pass_language()
# The window's parts (gui/), imported once the tweaks are read in the window's language: some
# read their text as they load.
from wallet_page import WalletApps  # noqa: E402  (Wallet apps page)
from packs_page import Packs  # noqa: E402  (Packs page)
from prefs_page import Preferences, window_prefs  # noqa: E402  (⚙ Preferences page)
from report_page import ReportPage  # noqa: E402  (🐞 Report a problem page)
from window_logic import (GONE, KNOWN_ISSUES, RESTART, UNLOAD, close_prompt, in_terminal,  # noqa: E402
                          latest_release, self_update_check, status, status_text, update_check)
from readme_view import follow_link, link_label, with_copy  # noqa: E402  (READMEs and links)
from tweak_rows import BREEZE, CONTRIBUTE, CategoryHeader, ContributeRow, Row, row_icon  # noqa: E402  (the list's rows)
from details_page import Details, ReadmePage  # noqa: E402  (a tweak's page, a README's)
from settings_page import SETTINGS_PAGES, SettingsPage  # noqa: E402  (⚙ Settings pages)
from apply_changes import ApplyChanges  # noqa: E402  (Apply changes, its confirm page)
from vr_controls import ControllerInput  # noqa: E402  (haptics and controller buttons in VR)
# Only re-exported: the tests reach these as gui.<name>, as they did before the window's parts
# moved out of this file. (Patching one here doesn't reach the module that uses it.)
import link_tip  # noqa: E402,F401  (re-exported for the tests)
import urllib.request  # noqa: E402,F401  (re-exported for the tests)
from PyQt6.QtCore import QUrl  # noqa: E402,F401  (re-exported for the tests)
from sft import release_channel  # noqa: E402,F401  (re-exported for the tests)
from window_logic import UNAVAILABLE, newest_release, release_key, version_tuple  # noqa: E402,F401  (re-exported for the tests)
from readme_view import (full_height, literal_placeholders, md_text, plain_markdown,  # noqa: E402,F401  (re-exported for the tests)
                         readme_browser, to_heading)
from settings_page import SettingsSection, running_action  # noqa: E402,F401  (re-exported for the tests)
ICONS = Path.home() / ".local/share/icons/hicolor/256x256/apps"
KNOWN_ISSUES.update({c["id"]: c["known_issue"] for c in components() if c["known_issue"]})   # (window_logic's)

STYLE = """
QWidget { background: #0b1016; color: #e8ecf0; font-size: 14px; }
QLabel#title { font-size: 20px; font-weight: 600; }
QWidget#cathead QPushButton#cattoggle { background: transparent; border: none; text-align: left;
                  font-size: 13px; font-weight: 700; color: #7fb2e5; letter-spacing: 1px; padding: 10px 4px 2px 4px; }
QWidget#cathead QPushButton#cattoggle:hover { color: #a9cdf0; }
QWidget#cathead QPushButton#cathide { padding: 3px 10px; font-size: 12px; margin-top: 8px; }
QWidget#cathead QPushButton#cattick { padding: 3px; margin-top: 8px; }
QLabel#category { font-size: 13px; font-weight: 700; color: #7fb2e5; letter-spacing: 1px;
                  padding: 10px 4px 2px 4px; }
QLabel#name { font-size: 15px; font-weight: 600; }
QLabel#desc { color: #9aa6b2; }
QLabel[status="ok"] { color: #5cc77a; } QLabel[status="warn"] { color: #e0b33a; }
QLabel[status="missing"], QLabel[status="checking"] { color: #6b7783; }
QWidget#row { background: #161c23; border-radius: 10px; }
QToolTip { font-size: 18px; padding: 8px 10px; color: #e8ecf0; background: #1f2731;
           border: 1px solid #355b7a; border-radius: 6px; }
QWidget#row:hover { background: #1c242d; }
QWidget#row[hidden_row="true"] { background: #11161c; }
QWidget#row[focused="true"] { background: #1f2a36; border: 2px solid #7fb2e5; }
QWidget#row QLabel, QWidget#row QCheckBox, QWidget#row QWidget#spacer { background: transparent; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2c333b, stop:0.5 #232a32, stop:1 #1c232a);
              border: none; border-bottom: 3px solid #0c1015; border-radius: 8px; padding: 6px 14px; }
QPushButton:hover { background: #3d4855; }
QPushButton:checked { background: #355b7a; }
QPushButton#apply { background: #355b7a; font-weight: 600; }
QPushButton#apply:disabled { background: #161c23; color: #3a434d; }
QPushButton#danger { background: #7a2e2e; font-weight: 600; }
QPushButton#danger:hover { background: #963838; }
QWidget#ask { background: #141b23; border: 1px solid #2a3542; border-radius: 8px; }
QPushButton#info { padding: 6px 10px; }
QPushButton#info:disabled { color: #3a434d; }
QWidget#timer { background: transparent; }
QPushButton#again { padding: 0px 10px 3px 10px; font-size: 24px; font-weight: 600; }
QPushButton#again:disabled { color: #3a434d; }
QPushButton#run { background: #2f6b46; font-weight: 600; min-width: 92px; }
QPushButton#run:hover { background: #3c8a5a; }
QPushButton#run:disabled { background: #161c23; color: #3a434d; }
QPushButton#run[help="true"] { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2c333b, stop:0.5 #232a32, stop:1 #1c232a); font-weight: 400; }
QCheckBox { padding: 8px; }
QCheckBox::indicator { width: 33px; height: 33px; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #11161c; width: 28px; margin: 0 0 0 6px; border-radius: 11px; }
QScrollBar:horizontal { background: #11161c; height: 28px; margin: 6px 0 0 0; border-radius: 11px; }
QScrollBar::handle { background: #2f3a46; border: 1px solid #3a4756; border-radius: 9px; margin: 2px; }
QScrollBar::handle:vertical { min-height: 56px; }
QScrollBar::handle:horizontal { min-width: 56px; }
QScrollBar::handle:hover { background: #3d4b5a; border-color: #4f6175; }
QScrollBar::handle:pressed { background: #355b7a; border-color: #7fb2e5; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: none; background: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QWidget#row[cta="true"] { background: #142130; border: 1px solid #2c4a66; }
QWidget#row[cta="true"]:hover { background: #18283a; }
QTextBrowser { background: #11161c; border: none; border-radius: 8px; padding: 8px; }
QLabel#issue { background: #2a2312; color: #e0b33a; border-radius: 8px; padding: 10px; }
QLabel#notice { color: #e0b33a; }
"""
# Tick boxes draw an empty box when unticked, so every row shows where to click.
_BOX = Path(__file__).resolve().parent / "images"
STYLE += f"""
QCheckBox::indicator:unchecked {{ image: url({_BOX}/box.svg); }}
QCheckBox::indicator:unchecked:hover {{ image: url({_BOX}/box-hover.svg); }}
QCheckBox::indicator:checked {{ image: url({_BOX}/box-checked.svg); }}
QRadioButton {{ padding: 8px; }}
QRadioButton::indicator {{ width: 33px; height: 33px; }}
QRadioButton::indicator:unchecked {{ image: url({_BOX}/radio.svg); }}
QRadioButton::indicator:unchecked:hover {{ image: url({_BOX}/radio-hover.svg); }}
QRadioButton::indicator:checked {{ image: url({_BOX}/radio-checked.svg); }}
"""

# Controller buttons in VR (B back, Y to the top, A ticks the row, the left D-pad through the
# rows; vrbuttons.py), read from the controller's model while the laser is on the window.
CONTROLLER_BUTTONS = True

# A row whose button opens a page of its own instead of settings (SETTINGS_PAGES) or Run (label,
# page): the wallet's apps.
PAGES = {"wallet": (N_("🔑 Wallet apps"), WalletApps)}         # (label: translated where it's shown)


class Window(ApplyChanges, ControllerInput, QWidget):
    """The installer window. Apply changes (apply_changes.py) and the controller in VR
    (vr_controls.py) are parts of it in modules of their own: mixins, before QWidget so their
    eventFilter is the one Qt calls."""
    pack_job = None         # a pack being added or updated from a link, (future, done, saying): finish_pack_job

    def __init__(self):
        super().__init__()
        # The build this window runs: the checkout can change under it (an update in a terminal,
        # a git pull), and until it restarts, it's this one's code that runs.
        self.build_at_start = version = sft.build_version()
        self.setWindowTitle(f"Frame Tweaks {version}")
        icon = ICONS / "frame-tweaks.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.setStyleSheet(STYLE)
        self.resize(1000, 760)
        self.rows = components()
        self.state = {}               # id -> (code, text); missing = still checking
        self.boxes, self.status_labels, self.wanted, self.run_buttons = {}, {}, {}, {}
        self.again_buttons = {}
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.futures = {}
        self.latest = {}              # id -> newest upstream tag (known-issue rows), None if unknown
        self.latest_futures = {}
        self.tidied = False           # tidy_unneeded ran (once the first round of statuses is in)
        self.check_known_issues()
        self.details = None
        self.updates, self.update_futures = {}, {}     # id -> (installed, latest) when newer
        self.prefs = window_prefs()
        try:                                         # (what's kept under a tweak's former id: formerly:)
            sft.apply_formerly()
        except OSError:
            pass
        self.self_update = self.pool.submit(self_update_check) if self.prefs["update_check"] else None
        # packs added from a link whose source has a newer version (with Frame Tweaks' own check)
        self.pack_updates = set()
        self.pack_check = self.pool.submit(sft.packs_with_updates) if self.prefs["update_check"] else None

        self.release_at_start = current_release()
        self.update_state, self.update_newest = "check", None
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(20, 16, 20, 16)
        self.stack = None
        self.build_ui()
        # Results of background jobs (status checks, update checks): looked for 10x a second while
        # any is running, once a second otherwise (collect sets which).
        self.collector = QTimer(self, interval=100, timeout=self.collect)
        self.collector.start()
        QTimer(self, interval=int(i18n.CHECK_EVERY * 1000), timeout=self.check_language).start()
        self.vr_buttons = None
        if os.environ.get("DISPLAY") == ":0":          # opened in VR: haptic ticks (and the controller buttons, when on)
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from vrbuttons import VRButtons
            self.vr_buttons = VRButtons({"back": self.go_back, "home": self.go_home,
                                         "toggle": self.toggle_pointed_row,
                                         "up": lambda: self.move_focus(-1),
                                         "down": lambda: self.move_focus(+1)}
                                        if CONTROLLER_BUTTONS else {})
            if self.vr_buttons.started:
                QApplication.instance().installEventFilter(self)    # haptics: see eventFilter
            if self.vr_buttons.ok:
                self._laser = (None, 0.0)
                # 30x a second while the laser is on the window; 4x a second otherwise, only to
                # notice it arriving (and which buttons are already held when it does).
                self.vr_timer = QTimer(self, interval=33, timeout=self.poll_vr_buttons)
                self.vr_timer.start()
        self.refresh()

    def build_ui(self):
        """The window's widgets (again after a change of language: retranslate)."""
        top = QHBoxLayout()
        title = QLabel(f"Frame Tweaks <span style='color:#6b7783;font-size:14px'>{self.running_build()}</span>")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch(1)
        self.self_update_label = QLabel()
        self.self_update_label.setObjectName("notice")
        self.self_update_label.linkActivated.connect(lambda _: self.run_update(None))
        top.addWidget(self.self_update_label)
        self.pack_update_label = QLabel()
        self.pack_update_label.setObjectName("notice")
        self.pack_update_label.linkActivated.connect(lambda _: self.show_packs())
        top.addWidget(self.pack_update_label)
        self.show_pack_updates()
        prefs = QPushButton("⚙")
        prefs.setToolTip(_("Preferences: the language, and how this window behaves"))
        prefs.clicked.connect(self.show_prefs)
        top.addWidget(prefs)
        self.show_hidden = QPushButton()
        self.show_hidden.setCheckable(True)
        self.show_hidden.toggled.connect(self.rebuild)
        top.addWidget(self.show_hidden)
        packs = QPushButton(_("🧩 Packs"))
        packs.setToolTip(_("Where the tweaks come from; add other people's (docs/mods.md)"))
        packs.clicked.connect(self.show_packs)
        top.addWidget(packs)
        refresh = QPushButton(_("Refresh"))
        refresh.clicked.connect(self.refresh)
        top.addWidget(refresh)

        self.list = QWidget()
        self.grid = QVBoxLayout(self.list)
        self.grid.setSpacing(8)
        scroll = QScrollArea()
        self.scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.list)

        bottom = QHBoxLayout()
        # One line on the left: how the list works, or for a few seconds a message (say()).
        self.hint_text = _("Tick to install, untick to remove, then Apply changes. "
                           "Click a row for details, a category to fold it.")
        self.notice = QLabel(self.hint_text)
        self.notice.setObjectName("desc")
        self.notice.setWordWrap(True)
        bottom.addWidget(self.notice, 1)
        self.update_button = QPushButton()
        self.update_button.clicked.connect(self.update_clicked)
        bottom.addWidget(self.update_button)
        self.set_update_state(self.update_state, self.update_newest)
        about = QPushButton(_("📖 README"))
        about.setToolTip(_("What Frame Tweaks is, how to install, update and remove it, common issues"))
        about.clicked.connect(self.show_readme)
        bottom.addWidget(about)
        diag = QPushButton(_("🐞 Report a problem"))
        diag.setToolTip(_("Save a diagnostics report (user names and paths removed) and open the bug form"))
        diag.clicked.connect(self.show_report)
        bottom.addWidget(diag)
        apply_ = QPushButton(_("Apply changes"))
        apply_.setObjectName("apply")
        apply_.clicked.connect(self.apply)
        self.apply_button = apply_
        close = QPushButton(_("Close"))
        close.clicked.connect(self.close)
        bottom.addWidget(apply_)
        bottom.addWidget(close)

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(top)
        lay.addWidget(self.make_password_bar())
        lay.addWidget(scroll, 1)
        lay.addLayout(bottom)
        self.row_widgets, self.focus_index = [], -1
        old = self.stack
        self.stack = QStackedWidget()
        self.stack.addWidget(page)
        self.confirm_page, self.confirm_text, self.confirm_yes = self.make_confirm_page()
        self.stack.addWidget(self.confirm_page)
        self.error_page, self.error_text = self.make_error_page()
        self.stack.addWidget(self.error_page)
        self.outer.addWidget(self.stack)
        if old is not None:
            self.outer.removeWidget(old)
            old.deleteLater()

    def check_language(self):
        """Every 5 s: has the keyboard's language changed (lib/i18n.py)? Then the window's text
        follows, once you're back on the list (an open page isn't pulled away from you)."""
        if self.stack.currentIndex() == 0 and self.details is None and i18n.refresh():
            pass_language()
            self.retranslate()

    def retranslate(self):
        showing = self.show_hidden.isChecked()
        sft.load(refresh=True)
        sft.SETTINGS = sft.settings_specs()
        KNOWN_ISSUES.clear()                             # (in place: window_logic.KNOWN_ISSUES)
        KNOWN_ISSUES.update({c["id"]: c["known_issue"] for c in components() if c["known_issue"]})
        self.rows = components()
        sft.not_needed(self.rows, refresh=True)          # (why one isn't needed, as its needed.sh says: in the new language)
        self.build_ui()
        self.show_hidden.blockSignals(True)
        self.show_hidden.setChecked(showing)
        self.show_hidden.blockSignals(False)
        if self.update_newest and self.update_state == "update":
            self.show_newest(self.update_newest)
        self.refresh()                                   # (statuses again, in the new language)

    # ---- hidden rows: yours, plus defaults you haven't unhidden ----------------
    def hidden(self):
        return sft.hidden(self.rows)

    def toggle_collapsed(self, category):
        """category: its English name (category_en), whatever the window's language."""
        collapsed = sft.read_categories(COLLAPSED, self.rows)
        collapsed ^= {category}
        write_set(COLLAPSED, collapsed)
        self.rebuild()

    def tick_category(self, category, on):
        """Tick (on) or untick every tweak in a category (its English name) that the list shows:
        not the hidden ones (unless shown), and when ticking, not those this Frame doesn't need.
        As if each box were clicked: nothing is installed or removed until Apply changes. (A
        folded category has no boxes: what's wanted is set all the same.)"""
        hidden, showing = self.hidden(), self.show_hidden.isChecked()
        not_needed = sft.not_needed(self.rows) if on else {}
        for c in self.rows:
            cid = c["id"]
            if c["category_en"] != category or (cid in hidden and not showing):
                continue
            if cid in not_needed and not sft.installed_record(cid):
                continue
            box = self.boxes.get(cid)
            if box is not None:
                box.setChecked(on)                      # (its toggled sets wanted)
            else:
                self.wanted[cid] = on
        self.update_apply()

    def toggle_category_hidden(self, category):
        sft.set_category_hidden(category, category not in sft.read_categories(HIDDEN_CATS, self.rows))
        self.rebuild()

    def toggle_hidden(self, cid):
        sft.set_hidden(cid, cid not in self.hidden())
        self.rebuild()

    # ---- status, in the background ------------------------------------------------
    def refresh(self):
        for fut in self.futures.values():            # (the last round's still waiting for a worker: not run as well)
            fut.cancel()
        self.state = {}
        self.futures = {c["id"]: self.pool.submit(status, c["id"]) for c in self.rows}
        self.collecting()
        self.rebuild()

    def collecting(self):
        """Background jobs were started: look for their results often again (collect)."""
        self.collect_every(100)

    def collect_every(self, ms):
        try:
            if self.collector.interval() != ms:
                self.collector.setInterval(ms)
        except (AttributeError, RuntimeError):       # (before the timer exists, or in a test's bare window)
            pass

    def collect(self):
        for cid, fut in list(self.latest_futures.items()):
            if fut.done():
                del self.latest_futures[cid]
                if fut.cancelled():                      # (the window closing)
                    continue
                self.latest[cid] = fut.result()
                if getattr(self.details, "comp", {}).get("id") == cid:
                    self.details.show_issue(self.latest[cid])
        if self.self_update is not None and self.self_update.done():
            job, self.self_update = self.self_update, None       # (cleared first: a check that failed came back every tick)
            try:
                newest = None if job.cancelled() else job.result()
            except Exception:
                newest = None
            if newest:
                self.show_newest(newest)
                if self.update_state in ("check", "checking"):
                    self.set_update_state("update", newest)
            elif self.update_state == "checking" and newest == "" and sft.build_version() != self.running_build():
                # Nothing newer on GitHub, but the checkout changed since this window opened: what's
                # on disk is newer than what runs here (an update in a terminal, a git pull).
                self.set_update_state("restart")
                self.say(_("Frame Tweaks was updated to {version} since this window opened: ↻ Restart to use "
                           "it.").format(version=sft.build_version()), good=True)
            elif self.update_state == "checking":
                left = sft.unfinished_update() if newest == "" else []
                self.set_update_state("finish" if left else "check")
                if newest is None:                       # (offline, say: not "up to date")
                    self.say(_("Couldn't check for updates (no connection to GitHub?)."))
                elif left:                               # (an update cut short: the checkout's new, these aren't)
                    self.say(_("The last update didn't finish: {tweaks} weren't installed again. ⬇ Finish the "
                               "update does it.").format(tweaks=", ".join(left)))
                else:
                    self.say(_("✔ Frame Tweaks is up to date ({version}).").format(version=self.running_build()),
                                             good=True)
        if self.pack_check is not None and self.pack_check.done():
            try:
                found = self.pack_check.result()
            except Exception:                            # (a pack's git saying something odd)
                found = []
            self.pack_check = None
            self.pack_updates = {p["dir"] for p in found}
            self.show_pack_updates()
            self.follow_packs()                          # (it read the packs again: one changed outside, say)
            if isinstance(self.details, Packs):
                self.details.build()
        self.finish_pack_job()
        shown = False
        for cid, fut in list(self.update_futures.items()):
            if fut.done():
                del self.update_futures[cid]
                found = None if fut.cancelled() or fut.exception() is not None else fut.result()
                state = self.state.get(cid)
                if found and (state is None or state[0] not in GONE):
                    self.updates[cid] = found
                else:                                    # (up to date now, or uninstalled meanwhile)
                    self.updates.pop(cid, None)
                self.show_status(cid)
                shown = True
        for cid, fut in list(self.futures.items()):
            if fut.done():
                del self.futures[cid]
                if fut.cancelled():                      # (the window closing)
                    continue
                try:
                    self.state[cid] = fut.result()
                except Exception as e:                   # (said on its row, rather than "checking…" for good)
                    self.state[cid] = (2, _("status check failed: {error}").format(error=str(e) or type(e).__name__))
                c = component(cid)
                if self.state[cid][0] in GONE:
                    self.updates.pop(cid, None)          # (not installed: nothing to update)
                elif c is not None and sft.script(c, "update-check") is not None:
                    self.update_futures[cid] = self.pool.submit(update_check, cid)
                self.show_status(cid)
                shown = True
                if cid in self.status_labels:
                    label = self.status_labels[cid]
                    text, kind = status_text(self.state[cid])
                    label.setProperty("status", kind)
                    label.style().unpolish(label)
                    label.style().polish(label)
                    self.update_run(cid)
                    self.update_again(cid)
                    box = self.boxes.get(cid)
                    if box is not None and cid not in self.wanted:
                        box.blockSignals(True)
                        box.setChecked(self.state[cid][0] not in GONE)
                        box.blockSignals(False)
                self.update_apply()
        try:
            tidy = shown and not self.futures and not self.tidied
        except (AttributeError, RuntimeError):            # (a test's bare window)
            tidy = False
        if tidy:
            self.tidy_unneeded()
        if shown:
            self.fit_list()                              # (a status can make its row wider)
        busy = (self.futures or self.latest_futures or self.update_futures or self.self_update is not None
                or self.pack_check is not None or self.pack_job is not None)
        self.collect_every(100 if busy else 1000)

    # ---- layout -----------------------------------------------------------------
    def rebuild(self, *_args):
        self.row_widgets, self.focus_index = [], -1
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        hidden = self.hidden()
        # (groups by their English name, category_en: the shown one follows the language)
        hidden_cats = sft.read_categories(HIDDEN_CATS, self.rows) & {c["category_en"] for c in self.rows}
        collapsed = sft.read_categories(COLLAPSED, self.rows)
        showing = self.show_hidden.isChecked()
        n_hidden = sum(1 for c in self.rows if c["id"] in hidden and c["category_en"] not in hidden_cats)
        n_hidden += len(hidden_cats)
        self.show_hidden.setText(_("Show hidden ({n})").format(n=n_hidden))
        self.show_hidden.setEnabled(n_hidden > 0 or showing)
        self.boxes, self.status_labels, self.run_buttons, self.again_buttons = {}, {}, {}, {}
        not_needed = sft.not_needed(self.rows)
        category = None
        for comp in self.rows:
            cid = comp["id"]
            cat, key = comp["category"], comp["category_en"]
            is_hidden = cid in hidden
            if key in hidden_cats and not showing:
                continue
            if is_hidden and not showing:
                continue
            if cat != category:
                category = cat
                count = sum(1 for c in self.rows if c["category"] == cat and (showing or c["id"] not in hidden))
                self.grid.addWidget(CategoryHeader(self, cat, count, key in collapsed, key in hidden_cats, key))
            if key in collapsed:
                continue
            row = Row(self, comp)
            self.row_widgets.append(row)
            row.setProperty("hidden_row", "true" if is_hidden else "false")
            g = QGridLayout(row)
            g.setContentsMargins(8, 10, 12, 10)
            g.setHorizontalSpacing(14)
            box = QCheckBox()
            state = self.state.get(cid)
            box.setChecked(self.wanted.get(cid, state[0] not in GONE if state else False))
            box.setToolTip(_("Tick to install, untick to remove"))
            why_not = not_needed.get(cid)
            if why_not is not None and not sft.installed_record(cid):    # (installed: untick to remove)
                box.setEnabled(False)
                box.setToolTip(_("Not needed on this Frame: %s") % why_not)
            box.toggled.connect(lambda on, c=cid: (self.wanted.__setitem__(c, on), self.update_apply()))
            self.boxes[cid] = box
            icon = QLabel()
            icon.setPixmap(row_icon(cid).pixmap(40, 40))
            sudo = sft.sudo_note(comp)
            name = QLabel(html.escape(comp["title"], quote=False) +
                          ("  🧪" if comp["experimental"] else "") +
                          ("  🔗" if comp["link"] else "") +
                          ("  <span style='color:#e0b33a;font-size:12px'>sudo</span>" if sudo else "") +
                          ("" if comp["official"] else
                           f"  <span style='color:#e0b33a;font-size:12px'>🧩 {html.escape(comp['pack'])}</span>") +
                          ("  <span style='color:#6b7783'>" + _("(hidden)") + "</span>" if is_hidden else ""))
            name.setObjectName("name")
            tips = []                                      # (one tooltip says each of them)
            if comp["experimental"]:
                tips.append(_("Experimental: %s") % comp["experimental"])
            if comp["link"]:
                tips.append(_("Linked: installed and uninstalled with the project's own commands, which Frame "
                              "Tweaks runs but doesn't check"))
            if sudo:
                tips.append(_("Asks for your sudo password: %s") % sudo)
            if not comp["official"]:
                tips.append((_("From the pack {pack}, not part of Frame Tweaks; used instead of {other}'s")
                             if comp["replaced"] else _("From the pack {pack}, not part of Frame Tweaks")).format(
                                pack=comp["pack"], other=comp["replaced"]))
            if tips:
                name.setToolTip("\n\n".join(tips))
            deps = comp["deps"]
            info = QLabel(html.escape(comp["desc"], quote=False) +
                          ("  <i style='color:#6b7783'>" + _("needs: %s") % ", ".join(deps) + "</i>" if deps else ""))
            info.setObjectName("desc")
            info.setWordWrap(True)
            if cid in KNOWN_ISSUES:
                info.setText(info.text() + "<br><span style='color:#e0b33a'>"
                             f"{html.escape(KNOWN_ISSUES[cid]['short'], quote=False)}</span>")
            if why_not is not None:
                info.setText(info.text() + "<br><span style='color:#e0b33a'>" + html.escape(
                    _("Not needed on this Frame: %s") % why_not, quote=False) + "</span>")
            link = QLabel()
            if "|" in comp["source"]:
                rel, url = comp["source"].split("|", 1)
                rel = _(rel)
                short = url.split("://", 1)[-1].removeprefix("github.com/").rstrip("/")
                if url.startswith("https://github.com/"):
                    short = "/".join(short.split("/")[:2])      # owner/repo; the link has the rest
                link_label(link).setText(with_copy(
                    f"<span style='color:#6b7783'>{html.escape(rel)}</span> "
                    f"<a style='color:#7fb2e5' href='{url}'>{html.escape(short)} ↗</a>"))
                link.setToolTip(_("Open %s") % url)
            text, kind = status_text(state)
            st = QLabel(text)
            st.setProperty("status", kind)
            st.setWordWrap(True)
            st.setTextFormat(Qt.TextFormat.RichText)
            st.linkActivated.connect(lambda _, c=cid: self.run_update(c))
            self.status_labels[cid] = st
            self.show_status(cid)
            run = QPushButton()
            run.setObjectName("run")
            self.run_buttons[cid] = run
            self.update_run(cid)
            run.clicked.connect(lambda _=False, c=comp: self.run(c))
            details = QPushButton("ⓘ")
            details.setObjectName("info")
            details.setToolTip(_("Details: what it is, why it's included, who made it"))
            details.clicked.connect(lambda _=False, c=comp: self.show_details(c))
            again = QPushButton("↻")
            again.setObjectName("again")
            again.clicked.connect(lambda _=False, c=cid: self.run_reinstall(c))
            self.again_buttons[cid] = again
            self.update_again(cid)
            hide = QPushButton(_("Unhide") if is_hidden else _("Hide"))
            hide.setToolTip(_("Show this tweak in the list again") if is_hidden else
                            _("Hide this tweak from the list (doesn't remove it)"))
            hide.clicked.connect(lambda _=False, c=cid: self.toggle_hidden(c))
            g.addWidget(box, 0, 0, 3, 1)
            g.addWidget(icon, 0, 1, 3, 1)
            g.addWidget(name, 0, 2)
            g.addWidget(info, 1, 2)
            if link.text():
                g.addWidget(link, 2, 2)
            g.addWidget(st, 0, 3, 3, 1)
            g.addWidget(run, 0, 4, 3, 1)
            col = 5
            if cid in SETTINGS_PAGES and run_label(cid):   # both a Run and settings: ⚙ beside Run
                gear = QPushButton("⚙")
                gear.setObjectName("info")
                gear.setToolTip(_("Settings"))
                gear.clicked.connect(lambda _=False, c=cid: self.open_settings(c))
                g.addWidget(gear, 0, col, 3, 1)
                col += 1
            g.addWidget(again, 0, col, 3, 1)
            g.addWidget(details, 0, col + 1, 3, 1)
            g.addWidget(hide, 0, col + 2, 3, 1)
            g.setColumnStretch(2, 3)
            g.setColumnStretch(3, 2)
            self.grid.addWidget(row)
        self.add_contribute_row()
        self.grid.addStretch(1)
        self.update_apply()
        self.fit_list()

    def fit_list(self):
        """The window is never narrower than the list's widest row: the list doesn't scroll
        sideways, so the buttons past a row's right edge (Hide, ↻, ⓘ, then Run) couldn't be reached.
        Nor is a Run button narrower than its text: the style sheet's min-width, set again each time
        it's styled (update_run), would let a narrow window squeeze "⟳ Restart SteamVR" to that.
        (Each row measured itself: rows just built aren't shown yet, so the list's layout leaves
        them out until they are.)"""
        for button in self.run_buttons.values():
            button.setMinimumWidth(button.sizeHint().width())
        rows = (self.grid.itemAt(i).widget() for i in range(self.grid.count()))
        widest = max((r.minimumSizeHint().width() for r in rows if r is not None), default=0)
        margins = self.grid.contentsMargins()
        bar = self.scroll.verticalScrollBar().sizeHint().width()
        self.scroll.setMinimumWidth(widest + margins.left() + margins.right() + bar + 2 * self.scroll.frameWidth())

    def add_contribute_row(self):
        """The list's last row, under every group whatever the packs' order (and whichever groups
        are folded or hidden): how to help (CONTRIBUTE), laid out as a tweak's row with nothing
        to install: no tick box or status, a call to action instead of Run."""
        self.grid.addSpacing(12)
        row = ContributeRow(self, CONTRIBUTE)
        self.row_widgets.append(row)
        row.setProperty("hidden_row", "false")
        row.setProperty("cta", "true")
        g = QGridLayout(row)
        g.setContentsMargins(8, 10, 12, 10)
        g.setHorizontalSpacing(14)
        spacer = QWidget()                           # (where a tweak's tick box is: the icons line up)
        spacer.setObjectName("spacer")
        spacer.setFixedWidth(QCheckBox().sizeHint().width())
        icon = QLabel()
        hits = sorted(BREEZE.glob(f"*/*/{CONTRIBUTE['icon']}.svg"))
        if hits:
            icon.setPixmap(QIcon(str(hits[-1])).pixmap(40, 40))
        name = QLabel(html.escape(_("Help make Frame Tweaks better"), quote=False))
        name.setObjectName("name")
        info = QLabel(html.escape(_("Have an idea for a tweak, or an app that belongs here? Found a bug, or speak "
                                    "another language? Every suggestion, report, translation and fix makes the Frame "
                                    "better for everyone who has one."), quote=False))
        info.setObjectName("desc")
        info.setWordWrap(True)
        read = QPushButton(_("Get involved"))
        read.setObjectName("apply")
        read.clicked.connect(self.show_contribute)
        g.addWidget(spacer, 0, 0, 2, 1)
        g.addWidget(icon, 0, 1, 2, 1)
        g.addWidget(name, 0, 2)
        g.addWidget(info, 1, 2)
        g.addWidget(read, 0, 4, 2, 1)
        g.setColumnStretch(2, 3)
        g.setColumnStretch(3, 2)
        self.grid.addWidget(row)

    def show_status(self, cid):
        """Status text, plus an Update link when upstream has a newer version; and on the tweak's
        page, if that's open, its status."""
        if isinstance(getattr(self, "details", None), Details) and self.details.comp["id"] == cid:
            self.details.show_state(self.state.get(cid))
        label = self.status_labels.get(cid)
        if label is None:
            return
        text, _kind = status_text(self.state.get(cid))
        text = html.escape(text, quote=False)
        if cid in self.updates:
            cur, new = self.updates[cid]
            text += ("<br><span style='color:#7fb2e5'>↑ " + _("{version} available").format(version=html.escape(new))
                     + " · <a style='color:#7fb2e5' href='u'>" + _("Update") + "</a></span>")
        label.setText(text)

    def run_update(self, cid, to=None):
        """Reinstall one tweak (fetches its latest upstream version), or update this repo (cid None;
        to: a release, or "stable" for the newest stable one)."""
        cmd = "./install.sh install " + shlex.quote(cid) if cid else "./install.sh update" + (
            " --to " + shlex.quote(to) if to else "")
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", cmd)
            return
        # (0 updated, 3 updated but a tweak didn't install again; else it didn't update: no "reopen")
        after = "" if cid else ("; rc=$?; if [ $rc -eq 0 ] || [ $rc -eq 3 ]; then echo; echo "
                                + shlex.quote(_("Close and reopen Frame Tweaks to use the new version.")) + "; fi")
        full = f"cd {shlex.quote(str(REPO))} && {cmd}{after}; echo; read -rp {close_prompt()}"
        self.proc = QProcess(self)
        self.proc.finished.connect(lambda *_: (self.updates.pop(cid, None), self.refresh(),
                                               cid is None and self.after_self_update()))
        in_terminal(self.proc, full)

    # ---- updating Frame Tweaks itself: Check for updates → Update to X → Restart --------
    def show_newest(self, newest):
        self.self_update_label.setText(
            "↑ " + _("{version} available").format(version=html.escape(newest)) + " · "
            "<a style='color:#7fb2e5' href='update'>" + _("Update") + "</a>")

    def set_update_state(self, state, newest=None):
        self.update_state, b = state, self.update_button
        self.update_newest = newest
        text, tip = {"check": (_("⟳ Check for updates"), _("Look for a newer Frame Tweaks release")),
                     "checking": (_("Checking…"), ""),
                     "update": (_("⬇ Update to {version}").format(version=newest),
                                _("Install it: your tweaks are updated with it")),
                     "restart": (_("↻ Restart"), _("Reopen Frame Tweaks to use the new version")),
                     "finish": (_("⬇ Finish the update"), _("Install the tweaks the last update didn't get to"))}[state]
        b.setText(text)
        b.setToolTip(tip)
        b.setEnabled(state != "checking")
        b.setObjectName("apply" if state in ("update", "restart") else "")
        b.style().unpolish(b)
        b.style().polish(b)

    def running_build(self):
        """The build this window runs (as it opened; sft.build_version() is the checkout's now)."""
        return getattr(self, "build_at_start", None) or sft.build_version()

    def show_pack_updates(self):
        """🧩 N pack updates, a link to the Packs page (packs added from a link; that page says which)."""
        n = len(getattr(self, "pack_updates", ()))
        self.pack_update_label.setText(
            ("🧩 <a style='color:#7fb2e5' href='packs'>" + ngettext("%d pack update", "%d pack updates", n) % n
             + "</a>") if n else "")
        self.pack_update_label.setToolTip(_("Packs added from a link have a newer version where they came from: "
                                            "the Packs page says which") if n else "")

    def update_clicked(self):
        if self.update_state == "check":
            self.set_update_state("checking")
            self.self_update = self.pool.submit(self_update_check)
            if self.pack_check is None:
                self.pack_check = self.pool.submit(sft.packs_with_updates)
            self.collecting()
        elif self.update_state in ("update", "finish"):
            self.run_update(None)
        elif self.update_state == "restart":
            self.restart_self()

    def channel_changed(self):
        """Test releases on or off (⚙ Preferences): a release found before may not be one to offer now."""
        if self.update_state != "restart":
            self.self_update_label.setText("")
            self.set_update_state("check")

    def after_self_update(self):
        """The updater's terminal closed: Restart if a new release is in place."""
        if current_release() != self.release_at_start:
            self.self_update_label.setText("")
            self.set_update_state("restart")

    def restart_self(self):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would restart the window")
            return
        # A new window from the same session (environment kept), once this one has let go of the
        # single-instance lock.
        QProcess.startDetached("bash", ["-c", 'sleep 1; exec "$0" gui', str(REPO / "install.sh")])
        QApplication.quit()

    def run_reinstall(self, cid):
        """Remove one tweak and install it again in one go (stops its running programs first)."""
        cmd = "./install.sh reinstall " + shlex.quote(cid)
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", cmd)
            return
        full = f"cd {shlex.quote(str(REPO))} && {cmd}; echo; read -rp {close_prompt()}"
        self.proc = QProcess(self)
        self.proc.finished.connect(lambda *_: self.changed([cid]))
        in_terminal(self.proc, full)

    def changed(self, ids):
        """The terminal that installed, reinstalled or removed these tweaks closed: an update found
        for them before is in now (or went with them), and every row is checked again."""
        for cid in ids:
            self.updates.pop(cid, None)
        self.refresh()

    def tidy_unneeded(self):
        """Installed tweaks this Frame doesn't need any more whose manifest says to remove them then
        (when_not_needed: uninstall; the Mouse cursor fix after a SteamOS update, or a switch to the
        beta, gave a second pointer until it was removed by hand): ./install.sh tidy removes them
        in the background, a notice says so, and the rows are checked again. Once per window; a
        login-time service does the same for people who don't open it."""
        if self.tidied:
            return
        self.tidied = True
        why = sft.not_needed(self.rows)
        gone = [c for c in self.rows if c.get("when_not_needed") == "uninstall" and c["id"] in why
                and self.state.get(c["id"]) is not None and self.state[c["id"]][0] not in GONE]
        if not gone:
            return
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):       # for tests: say what would run, change nothing
            print("would run: ./install.sh tidy")
            return
        titles = ", ".join(c["title"] for c in gone)
        reasons = "; ".join(why[c["id"]] for c in gone)
        ids = [c["id"] for c in gone]

        def done(code, *_args):     # (not *_: that would hide _(), the translations)
            if code == 0:
                self.say(_("Removed {tweaks}: not needed on this Frame ({why}). Some changes show after a "
                           "reboot.").format(tweaks=titles, why=reasons), good=True)
            else:
                self.say(_("Couldn't remove {tweaks} (not needed on this Frame): run ./install.sh tidy in a "
                           "terminal to see why.").format(tweaks=titles))
            self.changed(ids)
        self.tidy_proc = QProcess(self)
        self.tidy_proc.finished.connect(done)
        self.tidy_proc.start(str(REPO / "install.sh"), ["tidy"])

    def update_again(self, cid):
        """The ↻ Reinstall button: only for installed tweaks."""
        button = self.again_buttons.get(cid)
        if button is None:
            return
        state = self.state.get(cid)
        installed = state is not None and state[0] not in GONE
        button.setEnabled(installed)
        button.setToolTip(_("Reinstall: remove it and install it again in one step (settings kept)")
                          if installed else _("Reinstall (available once it's installed)"))

    def update_run(self, cid):
        """Run/Open/... for installed tweaks with something to launch, Help otherwise."""
        button = self.run_buttons.get(cid)
        if button is None:
            return
        state = self.state.get(cid)
        installed = state is not None and state[0] not in GONE
        label = run_label(cid)
        if state is not None and state[0] in (RESTART, UNLOAD):    # (until SteamVR restarts: no Run or Settings)
            button.setText(_("⟳ Restart SteamVR"))
            button.setProperty("help", "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.setEnabled(True)
            button.setToolTip(_("SteamVR loads it only as it starts. Every open app closes.") if state[0] == RESTART
                              else _("SteamVR runs it until it restarts. Every open app closes."))
            return
        if cid in PAGES:
            button.setText(_(PAGES[cid][0]))
            button.setProperty("help", "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.setEnabled(installed)
            button.setToolTip(_("Choose which apps open with the shared KDE wallet; lock or unlock it")
                              if installed else _("Tick it and Apply first"))
            return
        if cid in SETTINGS_PAGES and not label:          # (with something to run: a ⚙ beside it)
            button.setText(_("⚙ Settings"))
            button.setProperty("help", "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.setEnabled(installed)
            button.setToolTip(_("Settings") if installed else _("Settings (tick it and Apply first)"))
            return
        button.setText(("▶ " + label) if label else _("Help"))
        button.setProperty("help", "false" if label else "true")
        button.style().unpolish(button)
        button.style().polish(button)
        button.setEnabled(installed or label is None)
        button.setToolTip(_("{label} (installs first if needed: tick it and Apply)").format(label=label)
                          if label and not installed
                          else label and f"{label}" or _("Nothing to launch: how to use it"))

    def open_settings(self, cid):
        self.close_details()
        self.details = SETTINGS_PAGES[cid](self)             # a page: Back and B return to the list
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def run(self, comp):
        if (self.state.get(comp["id"]) or (None,))[0] in (RESTART, UNLOAD):
            self.restart_steamvr()
            return
        if comp["id"] in PAGES:
            self.close_details()
            self.details = PAGES[comp["id"]][1](self)            # a page: Back and B return to the list
            self.stack.addWidget(self.details)
            self.stack.setCurrentWidget(self.details)
            return
        if comp["id"] in SETTINGS_PAGES and not run_label(comp["id"]):
            self.close_details()
            self.details = SETTINGS_PAGES[comp["id"]](self)      # a page: Back and B return to the list
            self.stack.addWidget(self.details)
            self.stack.setCurrentWidget(self.details)
            return
        label = run_label(comp["id"])
        if label is None:
            self.show_details(comp)
            return
        c = component(comp["id"])
        cmd = sft.script(c, "run") if c else None      # (its run.sh, or a linked project's run: command)
        if cmd is None:                                 # (its folder went since the list was read: an update, say)
            self.say(_("Couldn't start {tweak}: its files aren't where they were when the list was read. "
                       "Close and reopen Frame Tweaks.").format(tweak=comp["title"]))
            return
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # (some restart things: Plasma, ydotoold)
            print("would run:", " ".join(cmd))
            return
        QProcess.startDetached(cmd[0], cmd[1:])
        # (a Restart, say, changes what its row should say: look again once it's had time)
        for ms in (3000, 10000):
            QTimer.singleShot(ms, lambda c=comp["id"]: self.recheck(c))

    def recheck(self, cid):
        """Check one row's status again (in the background, as the first time)."""
        if cid in self.futures or cid not in {c["id"] for c in self.rows}:
            return
        self.futures[cid] = self.pool.submit(status, cid)
        self.collecting()

    def changeEvent(self, ev):
        """Back to the window: rows that needed attention may not any more (desktop mode started
        since, say, and with it what the row waited for). Checked again, at most every 30 s."""
        super().changeEvent(ev)
        if ev.type() != QEvent.Type.ActivationChange or not self.isActiveWindow():
            return
        if time.monotonic() - getattr(self, "rechecked", 0) < 30:
            return
        self.rechecked = time.monotonic()
        for cid, st in list(getattr(self, "state", {}).items()):
            if st is not None and st[0] in (2, RESTART, UNLOAD):
                self.recheck(cid)

    def restart_steamvr(self):
        """⟳ Restart SteamVR, on the row of a tweak SteamVR loads only as it starts (installed, or
        uninstalled but still running): SteamOS's own restart (steamvr restart), which closes every
        app in the Steam session, desktop mode and this window too."""
        self.confirm(_("Restart SteamVR?") + "<br><br><span style='font-size:14px;color:#9aa6b2'>"
                     + html.escape(_("Every open app closes, desktop mode and this window too: save your work "
                                     "first. SteamVR then starts again by itself."), quote=False) + "</span>",
                     _("Restart SteamVR"), self.do_restart_steamvr)

    def do_restart_steamvr(self):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: steamvr restart")
            return
        # (With the VR session's runtime folder and D-Bus: steamvr restart goes through the user
        # service manager, which desktop mode's own can't reach. From the window in desktop mode
        # it failed, "Failed to connect to user scope bus", where nobody saw it: the script had
        # already exited fine.)
        run = f"/run/user/{os.getuid()}"
        if not QProcess.startDetached("env", [f"XDG_RUNTIME_DIR={run}", f"DBUS_SESSION_BUS_ADDRESS=unix:path={run}/bus",
                                              "steamvr", "restart"])[0]:
            self.say(_("Couldn't restart SteamVR; restart it from its menu, or reboot."))

    def show_details(self, comp, back=None):
        self.close_details()
        self.details = Details(self, comp, self.state.get(comp["id"]))
        self.details_back = back                     # (where its Back goes: see leave_details)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_tweak(self, cid):
        """That tweak's page (--show ID); nothing for an unknown id (from a pack not in use, say)."""
        comp = next((c for c in self.rows if c["id"] == cid), None)
        if comp is not None:
            self.show_details(comp)

    def show_contribute(self):
        self.close_details()
        self.details = ReadmePage(self, REPO / "docs/contribute.md", _("Help make Frame Tweaks better"))
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_readme(self):
        self.close_details()
        self.details = ReadmePage(self)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_report(self):
        self.close_details()
        self.details = ReportPage(self, follow_link, self.pool, REPO)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_prefs(self):
        self.close_details()
        self.details = Preferences(self, follow_link)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)

    def show_packs(self):
        self.close_details()
        self.details = Packs(self, follow_link, self.pool)          # (it reads the packs anew)
        self.stack.addWidget(self.details)
        self.stack.setCurrentWidget(self.details)
        self.follow_packs()

    def reload_tweaks(self):
        """After a pack was trusted or dropped: the list, settings and known issues anew."""
        sft.load(refresh=True)
        self.use_tweaks()

    def follow_packs(self):
        """sft read the packs again (the Packs page opening, Check for updates, a pack added or
        updated from a link): if the tweaks in use aren't the list's any more (a pack changed or
        turned off outside the window, say), the list follows. Its rows would ask sft for tweaks it
        no longer has."""
        if [(c["id"], c["dir"]) for c in components()] != [(c["id"], c["dir"]) for c in self.rows]:
            self.use_tweaks()

    def use_tweaks(self):
        """The list, settings and known issues of the tweaks sft has read."""
        sft.SETTINGS = sft.settings_specs()
        SETTINGS_PAGES.clear()
        SETTINGS_PAGES.update({cid: (lambda w, c=cid: SettingsPage(w, c)) for cid in sft.SETTINGS})
        KNOWN_ISSUES.clear()                             # (in place: window_logic.KNOWN_ISSUES)
        KNOWN_ISSUES.update({c["id"]: c["known_issue"] for c in components() if c["known_issue"]})
        self.check_known_issues()
        self.rows = components()
        self.refresh()

    def check_known_issues(self):
        """Has a known issue's app a newer release? Looked for once each, in the background: as the
        window opens, and for a tweak a pack brings later."""
        for cid, issue in KNOWN_ISSUES.items():
            if cid not in self.latest and cid not in self.latest_futures:
                self.latest_futures[cid] = self.pool.submit(latest_release, issue["latest"])
                self.collecting()

    def finish_pack_job(self):
        """A pack added or updated from a link (the Packs page's start), once its git clone or pull
        is done: its end goes to the Packs page open then (going Back meanwhile doesn't lose it),
        and the list follows the tweaks in use."""
        job = self.pack_job
        if job is None or not job[0].done():
            return
        self.pack_job = None
        fut, done, _saying = job
        if fut.cancelled():                          # (the window closing)
            return
        if isinstance(self.details, Packs):
            self.details.finished(fut, done)
        elif fut.exception() is None:
            done(None, fut.result())                 # (no page to tell: the window's part only)
        self.follow_packs()

    def close_details(self):
        if self.details is not None:
            self.stack.removeWidget(self.details)
            self.details.deleteLater()
            self.details = None
        self.stack.setCurrentIndex(0)
        self.details_back = None

    def leave_details(self):
        """Back on a page: to where it was opened from (the Packs page, for a tweak of a pack's
        inventory), else to the list."""
        back = getattr(self, "details_back", None)
        self.close_details()
        if back is not None:
            back()

    # ---- in-window messages (no dialogs: in VR they'd open in the dashboard) ----------
    def say(self, text, good=False):
        """A message on the left of the bottom bar for a few seconds: green when it's good news
        (as ✔ statuses), amber otherwise."""
        colour = "#5cc77a" if good else "#e0b33a"
        self.notice.setText(f"<span style='color:{colour}'>{html.escape(text)}</span>")
        shown = self.notice.text()
        QTimer.singleShot(6000, lambda: self.notice.text() == shown and self.notice.setText(self.hint_text))

    # ---- changes in a terminal (what Apply changes asks first: apply_changes.py) ------------
    def run_changes(self, add, remove):
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would remove:", " ".join(remove) or "none")
            print("would install:", " ".join(add) or "none")
            return
        steps = []
        if remove:
            steps.append("./install.sh uninstall " + " ".join(remove))
        if add:
            steps.append("./install.sh install " + " ".join(add))
        # (one splash for both: ./install.sh run under lib/splash.py doesn't start another)
        cmd = (f"cd {shlex.quote(str(REPO))} && python3 lib/splash.py -- bash -c {shlex.quote(' && '.join(steps))}"
               f"; echo; read -rp {close_prompt()}")
        self.proc = QProcess(self)            # don't block the window while Konsole runs
        self.proc.finished.connect(lambda *_: (self.wanted.clear(), self.changed(add + remove)))
        in_terminal(self.proc, cmd)

    def uninstall_self(self, keep_tweaks, settings, keep_apps=True):
        """⚙ Preferences → Uninstall Frame Tweaks: ./install.sh uninstall-self in a terminal, and this
        window closes (it runs from the folder and the Python setup that go)."""
        flags = (["--keep-tweaks"] if keep_tweaks else [] if keep_apps else ["--remove-apps"]) + [f"--{settings}-settings"]
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would run: ./install.sh uninstall-self " + " ".join(flags))
            return
        cmd = f"cd {shlex.quote(str(REPO))} && ./install.sh uninstall-self {' '.join(flags)}; echo; read -rp {close_prompt()}"
        # (detached: it must outlive this window, which quits at once)
        ok, _pid = QProcess.startDetached("bash", ["-c", 'exec konsole --separate -e bash -c "$1" >/dev/null 2>&1',
                                                  "konsole", cmd])
        if ok:
            QApplication.instance().quit()
        else:
            self.say(_("Couldn't open a terminal: run ./install.sh uninstall-self in {folder}").format(folder=REPO))

    # ---- back and home (Back buttons; B and Y on the controller in VR: vr_controls.py) ---------
    def go_back(self):
        if self.details is not None:
            self.leave_details()
        else:
            self.stack.setCurrentIndex(0)

    def go_home(self):
        self.close_details()
        self.scroll.verticalScrollBar().setValue(0)

    # ---- diagnostics and errors -------------------------------------------------
    def make_error_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        head = QLabel(_("Something went wrong in the installer window"))
        head.setObjectName("title")
        lay.addWidget(head)
        hint = QLabel(_("Copy the details into a bug report. The window keeps working: go back and try again."))
        hint.setObjectName("desc")
        lay.addWidget(hint)
        text = QTextBrowser()
        lay.addWidget(text, 1)
        buttons = QHBoxLayout()
        copy = QPushButton(_("Copy for bug report"))
        copy.clicked.connect(lambda: (QApplication.clipboard().setText(text.toPlainText()),
                                      copy.setText(_("Copied"))))
        back = QPushButton(_("← Back"))
        back.clicked.connect(lambda: (copy.setText(_("Copy for bug report")), self.close_details()))
        report = QPushButton(_("🐞 Report a problem"))
        report.setToolTip(_("Copy these details, then save a diagnostics report and open the bug form"))
        report.clicked.connect(lambda: (QApplication.clipboard().setText(text.toPlainText()), self.show_report()))
        buttons.addWidget(back)
        buttons.addStretch(1)
        buttons.addWidget(copy)
        buttons.addWidget(report)
        lay.addLayout(buttons)
        return page, text

    def show_error(self, kind, value, tb):
        """sys.excepthook: show it in the window (a dialog would open elsewhere in VR)."""
        import platform
        import traceback
        version = self.running_build()
        details = (f"Frame Tweaks {version}, Python {platform.python_version()}, {platform.machine()}\n\n"
                   + "".join(traceback.format_exception(kind, value, tb)))
        self.error_text.setPlainText(details.replace(str(Path.home()), "~"))
        self.stack.setCurrentWidget(self.error_page)
        sys.__excepthook__(kind, value, tb)

    def closeEvent(self, ev):
        if self.vr_buttons:
            self.vr_buttons.close()
        self.collector.stop()                       # (the jobs it would look at are cancelled now)
        self.pool.shutdown(wait=False, cancel_futures=True)
        for proc in self.findChildren(QProcess):    # (stopped as the window goes: their finished
            proc.blockSignals(True)                 # would refresh it, with the pool shut down)
        super().closeEvent(ev)


SERVER = f"frame-tweaks-gui-{os.getuid()}"


ANSWER_MS = 3000      # (how long an open window has to answer a second launch before it's taken as stuck)


def hand_over(tweak=""):
    """One window: a second launch asks the open one to come forward (on that tweak) and exits
    (True). The open one answers with its session: open in the other one (VR or desktop mode),
    that's where it came forward, so a notification says so. No answer: it's stuck, and is
    stopped so this launch opens a window instead of nothing (False, as with none open)."""
    probe = QLocalSocket()
    probe.connectToServer(SERVER)
    if not probe.waitForConnected(300):
        return False
    probe.write(f"show {tweak}".strip().encode())
    probe.waitForBytesWritten(300)
    # (the answer can be in before the wait: the open window writes it as soon as it connects)
    if probe.bytesAvailable() or probe.waitForReadyRead(ANSWER_MS) or probe.bytesAvailable():
        there, here = bytes(probe.readAll()).decode(errors="replace").strip(), browser.session_of(os.environ)
        if there and here and there != here:
            notify(_("Frame Tweaks is already open in {session}").format(session=_(there)),
                   _("It came to the front there. Close it there to open it here."))
        return True
    probe.abort()
    stop_stuck_windows()
    return False


def notify(title, body):
    """A notification, for a launch that opens no window of its own."""
    try:
        subprocess.Popen(["notify-send", "-a", "Frame Tweaks", title, body], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def stop_stuck_windows():
    """The open window didn't answer a second launch: it's stuck (or one from before an update
    that doesn't answer). Stop it, so the new one opens instead of nothing; noted in the log."""
    import signal
    pids = window_pids()
    for sig, wait in ((signal.SIGTERM, 2), (signal.SIGKILL, 0)):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except OSError:
                pass
        deadline = time.monotonic() + wait
        while wait and time.monotonic() < deadline and any(Path(f"/proc/{p}").exists() for p in pids):
            time.sleep(0.1)
    try:
        log = Path.home() / ".local/state/frame-tweaks/logs/window.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + f"an open window didn't answer: stopped it ({pids})\n")
    except OSError:
        pass


SCRIPT = Path(__file__).resolve()


def window_pids():
    """This user's other processes running this window: a Python (./install.sh runs it as
    sft-python) given this very script. Not an editor that has it open, say, nor any other command
    line that only names it."""
    try:
        out = subprocess.run(["pgrep", "-u", str(os.getuid()), "-f", "frame-tweaks-gui.py"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    pids = []
    for pid in (int(p) for p in out.split() if p.isdigit() and int(p) != os.getpid()):
        try:
            argv = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
            cwd = os.readlink(f"/proc/{pid}/cwd")          # (./install.sh gives it as gui/frame-tweaks-gui.py)
        except OSError:                                      # (it ended meanwhile)
            continue
        if len(argv) > 1 and re.fullmatch(r"sft-python|python[\d.]*", Path(argv[0]).name) \
                and (Path(cwd) / argv[1]).resolve() == SCRIPT:
            pids.append(pid)
    return pids


def watch_for_hangs(log_dir):
    """If the window stops responding (its event loop stalls 10 s), write where every thread is
    to log_dir/gui-hang-<time>.log: the next freeze leaves a clue instead of nothing."""
    import faulthandler
    import threading
    beat = [time.monotonic()]
    QTimer(QApplication.instance(), interval=1000, timeout=lambda: beat.__setitem__(0, time.monotonic())).start()

    def watch():
        reported = False
        while True:
            time.sleep(2)
            stalled = time.monotonic() - beat[0]
            if stalled > 10 and not reported:
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                    with open(log_dir / time.strftime("gui-hang-%Y%m%d-%H%M%S.log"), "w") as f:
                        f.write(f"The installer window's event loop stalled for {stalled:.0f} s. Threads:\n")
                        faulthandler.dump_traceback(f, all_threads=True)
                except OSError:
                    pass
                reported = True
            elif stalled < 3:
                reported = False
    threading.Thread(target=watch, daemon=True, name="hang-watch").start()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("frame-tweaks")
    app.setDesktopFileName("io.github.AstronautCheetah.FrameTweaks")
    # --show ID: open on that tweak's page (lib/needs.py: a feature that needs it, not installed).
    args = sys.argv[1:]
    tweak = args[args.index("--show") + 1] if "--show" in args[:-1] else ""
    if hand_over(tweak):
        return
    QLocalServer.removeServer(SERVER)
    server = QLocalServer()
    server.listen(SERVER)
    watch_for_hangs(Path.home() / ".local/state/frame-tweaks/logs")
    w = Window()

    def come_forward():
        conn = server.nextPendingConnection()
        if conn is not None:          # (the session it's open in: see above)
            conn.write((browser.session_of(os.environ) or "").encode())
            conn.flush()
        w.showNormal()
        w.raise_()
        w.activateWindow()
        if conn is not None:          # ("show ID": that tweak's page, once the message has arrived)
            conn.readyRead.connect(lambda: w.show_tweak(bytes(conn.readAll()).decode(errors="replace")[5:].strip()))
    server.newConnection.connect(come_forward)
    sys.excepthook = w.show_error
    app.aboutToQuit.connect(i18n.withdraw)          # (programs started later follow the keyboard again)
    w.show()
    if tweak:
        w.show_tweak(tweak)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
