"""The installer window's Packs page: the packs of tweaks it found (docs/mods.md), whether each is
in use, trusting or no longer using a user's pack, and what's wrong with any of them."""
import html
import subprocess

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QScrollArea, QToolTip, QVBoxLayout, QWidget

import browser  # (lib/ is on the path)
from i18n import _  # (translations: locale/README.md)
import sft

STATE = {"official": ("Comes with Frame Tweaks", "#5cc77a"),
         "trusted": ("Trusted: its tweaks are listed", "#5cc77a"),
         "untrusted": ("Not trusted yet: its tweaks aren't listed", "#e0b33a"),
         "changed": ("Changed since you trusted it: not used until you trust it again", "#e0b33a")}


class Packs(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("Packs"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        folder = QPushButton(_("Open packs folder"))
        folder.setToolTip(str(sft.USER_PACKS))
        folder.clicked.connect(self.open_folder)
        head.addWidget(folder)
        lay.addLayout(head)
        about = QLabel(
            "Every tweak here comes from a <b>pack</b>: a folder of tweak folders, each described by its "
            "README.md. Frame Tweaks' own tweaks are the official pack. To add more, put a pack in "
            f"<code>{html.escape(str(sft.USER_PACKS))}</code>, then trust it below. "
            "<b>A pack's tweaks run as you</b>, with your files and passwords in reach: trust only packs "
            "from people you trust, and read what they do first. If a pack's files change, it waits "
            "until you trust it again. How to write one: docs/mods.md.")
        about.setWordWrap(True)
        about.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(about)
        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.body)
        lay.addWidget(scroll, 1)
        self.confirming = None
        self.build()

    def build(self):
        while self.rows.count():
            w = self.rows.takeAt(0).widget()
            if w:
                w.deleteLater()
        data = sft.load(refresh=True)
        used = {c["id"]: c for c in data["components"]}
        for p in data["packs"]:
            row = QWidget()
            row.setObjectName("row")
            g = QHBoxLayout(row)
            g.setContentsMargins(12, 10, 12, 10)
            text, colour = STATE[p["state"]]
            tweaks = []
            for t in p["tweaks"]:
                c = used.get(t)
                mine = c is not None and c["pack_dir"] == p["dir"]
                tweaks.append(html.escape(t) + (f" <i>(instead of {html.escape(c['replaced'])}'s)</i>"
                                                if mine and c["replaced"] else ""))
            info = QLabel(f"<b>{html.escape(p['name'])}</b>"
                          + (f" <span style='color:#6b7783'>by {html.escape(p['author'])}</span>" if p["author"] else "")
                          + (f"<br>{html.escape(p['about'])}" if p["about"] else "")
                          + f"<br><span style='color:{colour}'>{text}</span>"
                          + f"<br><span style='color:#6b7783'>{html.escape(str(p['dir']))}</span>"
                          + (f"<br>{len(p['tweaks'])} tweaks" if p["state"] == "official" else
                             "<br>Tweaks: " + (", ".join(tweaks) or "none")))
            info.setWordWrap(True)
            info.setTextFormat(Qt.TextFormat.RichText)
            g.addWidget(info, 1)
            if p["state"] != "official":
                if p["state"] == "trusted":
                    b = QPushButton(_("Stop using"))
                    b.setToolTip("Its tweaks leave the list; installed ones stay until you uninstall them")
                    b.clicked.connect(lambda _=False, d=p["dir"]: self.trust(d, False))
                elif self.confirming == p["dir"]:
                    b = QPushButton(_("Yes: it runs as me"))
                    b.setToolTip("Trust this pack's current files")
                    b.clicked.connect(lambda _=False, d=p["dir"]: self.trust(d, True))
                else:
                    b = QPushButton(_("Trust…"))
                    b.clicked.connect(lambda _=False, d=p["dir"]: self.confirm(d))
                g.addWidget(b)
            self.rows.addWidget(row)
        if data["problems"]:
            probs = QLabel("<b>Problems</b><br>" + "<br>".join(html.escape(x) for x in data["problems"]))
            probs.setWordWrap(True)
            probs.setTextFormat(Qt.TextFormat.RichText)
            probs.setStyleSheet("color: #e0b33a")
            self.rows.addWidget(probs)
        self.rows.addStretch(1)

    def confirm(self, d):
        self.confirming = d
        self.build()

    def trust(self, d, on):
        self.confirming = None
        sft.set_trusted(d, on)
        self.window.reload_tweaks()
        self.build()

    def open_folder(self):
        sft.USER_PACKS.mkdir(parents=True, exist_ok=True)
        # The default file manager as desktop mode sets it, where it's running (lib/browser.py):
        # xdg-open from the VR session would pick Kate.
        note = browser.open_path(str(sft.USER_PACKS))
        if note:
            QToolTip.showText(QCursor.pos(), note)
        else:
            subprocess.Popen(["xdg-open", str(sft.USER_PACKS)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
