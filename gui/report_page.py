"""The installer window's 🐞 Report a problem page: it saves the diagnostics report
(./install.sh debug-info: versions, status, recent logs; user names, paths and addresses
removed), says where, and opens the bug form with the version filled in, to attach it to.
Nothing is sent anywhere by itself."""
import html
import os
import subprocess
import urllib.parse
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from i18n import _
import sft

BUG_FORM = "https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=bug_report.yml"


def bug_form_url(tweak=""):
    query = {"version": sft.build_version()}
    if tweak:
        query["tweak"] = tweak
    return BUG_FORM + "&" + urllib.parse.urlencode(query)


class ReportPage(QWidget):
    def __init__(self, window, follow_link, pool, repo):
        super().__init__()
        self.window, self.follow, self.path = window, follow_link, None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("Report a problem"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.text)
        steps = QLabel(_("1. Read the report: it's plain text, and nothing in it is sent anywhere unless you "
                         "attach it.<br>2. Open the bug form (on GitHub; you sign in there), say what happened "
                         "and what you expected, and drag the report into its Diagnostics report box."))
        steps.setWordWrap(True)
        steps.setTextFormat(Qt.TextFormat.RichText)
        steps.setObjectName("desc")
        lay.addWidget(steps)
        buttons = QHBoxLayout()
        self.open_report = QPushButton(_("📄 Open the report"))
        self.open_report.setEnabled(False)
        self.open_report.clicked.connect(lambda: self.path and self.follow(Path(self.path).as_uri()))
        buttons.addWidget(self.open_report)
        form = QPushButton(_("🐞 Open the bug form"))
        form.setObjectName("apply")
        form.clicked.connect(lambda: self.follow(bug_form_url()))
        buttons.addWidget(form)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        lay.addStretch(1)
        self.text.setText(_("Saving the diagnostics report…"))
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: ./install.sh debug-info")
            self.done = None
            self.text.setText(_("(Trying out the window: no report saved.)"))
            return
        self.done = pool.submit(subprocess.run, [str(repo / "install.sh"), "debug-info"],
                                capture_output=True, text=True)
        self.timer = QTimer(self, interval=200, timeout=self.collect)
        self.timer.start()

    def collect(self):
        if not self.done.done():
            return
        self.timer.stop()
        r = self.done.result()
        path = next((l.split(" ", 1)[1] for l in r.stdout.splitlines() if l.startswith("Wrote ")), None)
        if path:
            self.path = path
            self.open_report.setEnabled(True)
            self.text.setText(_("Saved <b>{file}</b>: Frame Tweaks' and SteamOS's versions, each tweak's "
                                "status and recent logs, with user names, paths, host and phone names and "
                                "addresses removed.").format(file=html.escape(path.replace(str(Path.home()), "~"))))
        else:
            self.text.setText(_("Couldn't write the report (see {command}).").format(command="./install.sh debug-info"))
