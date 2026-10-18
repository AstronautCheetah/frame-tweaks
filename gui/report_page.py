"""The installer window's 🐞 Report a problem page: it saves the diagnostics report
(./install.sh debug-info: versions, status, recent logs; with the names, addresses, tokens and
keys its first line lists removed), shows it right here (with a Copy button), and opens the bug
form with the version filled in, to paste or attach it to. Nothing is sent anywhere by itself.
It used to open the report in your text editor: in VR that started Kate, a Flatpak, as a VR
window, and SteamOS's Holo portal crashes as a KDE Flatpak starts there (five times in a row on
2026-10-17; KWalletManager did it too). Shown here, no other app starts."""
import html
import os
import subprocess
import urllib.parse
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from i18n import _
import sft

BUG_FORM = "https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=bug_report.yml"


TRANSLATION_FORM = "https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=translation_check.yml"


VOLUNTEER_FORM = "https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=translation_volunteer.yml"


def volunteer_form_url(language=""):
    """The form to offer a translation (a new language, or one made by machine), language filled in."""
    return VOLUNTEER_FORM + ("&" + urllib.parse.urlencode({"language": language}) if language else "")


def translation_form_url(language):
    """The translation check form, with the language (its code and name) and the version filled in."""
    return TRANSLATION_FORM + "&" + urllib.parse.urlencode({"language": language, "version": sft.build_version()})


def bug_form_url(tweak=""):
    query = {"version": sft.build_version()}
    if tweak:
        query["tweak"] = tweak
    return BUG_FORM + "&" + urllib.parse.urlencode(query)


class ReportPage(QWidget):
    """Laid out the same while the report is being saved and once it is (no jump when it's done):
    the steps, the buttons (Copy greyed until there's a report; where it was saved beside them),
    and the report's box, which says it's being saved until the report fills it."""

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
        # (what's removed: exactly what ./install.sh debug-info removes, as its first line lists)
        steps = QLabel(_("1. Read the report below: Frame Tweaks' and SteamOS's versions, each tweak's status and "
                         "recent logs. Removed from it: your user name, home folder path and host name, the phone "
                         "names Android Mirror remembers and adb's names for phones, IP, MAC and e-mail addresses, "
                         "GitHub tokens, and other tokens and keys written as 64 hex digits or as 44 base64 "
                         "characters ending in =. Anything else stays as it was. Nothing in it is sent anywhere "
                         "unless you add it to the form.<br>2. Open the bug form (on GitHub; you sign in there), say "
                         "what happened and what you expected, then paste the report into its Diagnostics report box "
                         "(📋 Copy the report), or attach the saved file."))
        steps.setWordWrap(True)
        steps.setTextFormat(Qt.TextFormat.RichText)
        steps.setObjectName("desc")
        lay.addWidget(steps)
        buttons = QHBoxLayout()
        self.copy = QPushButton(_("📋 Copy the report"))
        self.copy.setEnabled(False)
        self.copy.clicked.connect(self.copy_report)
        buttons.addWidget(self.copy)
        form = QPushButton(_("🐞 Open the bug form"))
        form.setObjectName("apply")
        form.clicked.connect(lambda: self.follow(bug_form_url()))
        buttons.addWidget(form)
        buttons.addStretch(1)
        self.saved = QLabel()                    # (where it was saved: on the buttons' line, so nothing moves)
        self.saved.setObjectName("desc")
        self.saved.setTextFormat(Qt.TextFormat.RichText)
        buttons.addWidget(self.saved)
        lay.addLayout(buttons)
        # The report itself, read-only (in its columns: a fixed-width font); until it's there, its box
        # says what's happening.
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setStyleSheet("font-family: monospace;")
        lay.addWidget(self.view, 1)
        self.view.setPlaceholderText(_("Saving the diagnostics report…"))
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run: ./install.sh debug-info")
            self.done = None
            self.view.setPlaceholderText(_("(Trying out the window: no report saved.)"))
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
        try:
            text = Path(path).read_text(errors="replace") if path else None
        except OSError:
            text = None
        if text is None:
            self.view.setPlaceholderText(_("Couldn't write the report (see {command}).").format(command="./install.sh debug-info"))
            return
        self.path = path
        self.view.setPlainText(text)
        self.copy.setEnabled(True)
        self.saved.setText(_("Saved as {file}").format(file="<b>" + html.escape(path.replace(str(Path.home()), "~")) + "</b>"))

    def copy_report(self):
        QApplication.clipboard().setText(self.view.toPlainText())
        self.copy.setText(_("📋 Copied"))
