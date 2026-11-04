"""The installer window's "Works on my Frame" page: a short report of which tweaks work on this
Frame's SteamOS and SteamVR builds, shown in full first, then GitHub's "Works on my Frame" issue
form opened in the browser with it filled in. Each click is one report, read and sent (or not) by
the person on GitHub: this page sends nothing, starts nothing in the background and remembers
nothing, as Frame Tweaks promises no telemetry. Each tweak's status goes in as its mark only (✔,
!, ⟳, ·): a status's own text can say personal things (a VPN's location, say)."""
import re
import subprocess
import urllib.parse
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from i18n import _
import sft
from window_logic import RESTART, UNLOAD, UNAVAILABLE

WORKS_FORM = "https://github.com/AstronautCheetah/frame-tweaks/issues/new?template=test_report.yml"
# (GitHub refuses a link much longer than this; the report is far shorter, but a long tweak list
# from many packs is cut rather than lost: the copy button has it all)
MAX_URL = 7000


def frame_versions(os_release=None, vr_log=None, channel=None):
    """{"steamos", "build", "steamvr", "channel"} as this Frame has them ("" when it can't tell):
    SteamOS's version and build from /etc/os-release, SteamVR's from its server log (its
    version.txt is a build number), the update channel from steamos-select-branch."""
    if os_release is None:
        try:
            os_release = Path("/etc/os-release").read_text(errors="replace")
        except OSError:
            os_release = ""
    if vr_log is None:
        try:
            vr_log = (Path.home() / ".local/share/Steam/logs/vrserver.txt").read_text(errors="replace")
        except OSError:
            vr_log = ""
    if channel is None:
        try:
            channel = subprocess.run(["steamos-select-branch", "-c"], capture_output=True, text=True,
                                     timeout=5).stdout.strip().splitlines()[-1:]
            channel = channel[0] if channel else ""
        except (OSError, subprocess.SubprocessError):
            channel = ""

    def field(name):
        m = re.search(rf'^{name}="?([^"\n]*)"?$', os_release, re.M)
        return m[1] if m else ""
    vr = re.search(r"vrserver ([0-9][0-9.]*) startup", vr_log)
    return {"steamos": field("VERSION_ID"), "build": field("BUILD_ID"), "steamvr": vr[1] if vr else "",
            "channel": channel}


def mark(code_text):
    """A status as its mark only (window_logic.status_text's), never its text."""
    if code_text is None:
        return "?"
    code = code_text[0]
    return {0: "✔", 1: "·", 2: "!", RESTART: "⟳", UNLOAD: "⟳", UNAVAILABLE: "·"}.get(code, "!")


def works_report(build, versions, state):
    """(versions, status): the form's two boxes, as plain text. state: {id: (code, text), or None
    while its check isn't back}, every row of the list, in its order."""
    lines = [f"Frame Tweaks {build}",
             f"SteamOS {versions['steamos'] or '?'} (build {versions['build'] or '?'}"
             + (f", {versions['channel']}" if versions["channel"] else "") + ")",
             f"SteamVR {versions['steamvr'] or '?'}"]
    status = [f"{mark(st)} {cid}" for cid, st in state.items()]
    return "\n".join(lines), "\n".join(status)


def works_form_url(versions_text, status_text):
    query = urllib.parse.urlencode({"versions": versions_text, "status": status_text})
    url = WORKS_FORM + "&" + query
    if len(url) > MAX_URL:
        url = WORKS_FORM + "&" + urllib.parse.urlencode({"versions": versions_text})
    return url


class WorksPage(QWidget):
    """The report in full, read-only, then the form: nothing leaves until the person submits it."""

    def __init__(self, window, follow_link):
        super().__init__()
        self.window = window
        # (every row in the list's order: window.state is in the order the checks came in, and
        # has no row whose check isn't back yet, which the report left out rather than "?")
        versions, status = works_report(sft.build_version(), frame_versions(),
                                        {c["id"]: window.state.get(c["id"]) for c in window.rows})
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(_("Works on my Frame"))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        steps = QLabel(_("Tell others which tweaks work on your SteamOS and SteamVR versions. Below is everything "
                         "the report says: the versions, and each tweak as a mark only (✔ works, ! needs "
                         "attention, ⟳ waits for a SteamVR restart, · not installed), not its status text.<br>"
                         "<b>Open the form on GitHub</b> opens it in your browser with this filled in. Nothing is "
                         "sent unless you submit it there (you sign in on GitHub, and the report is public). "
                         "Frame Tweaks sends nothing by itself and doesn't remember this."))
        steps.setWordWrap(True)
        steps.setTextFormat(Qt.TextFormat.RichText)
        steps.setObjectName("desc")
        lay.addWidget(steps)
        self.text = versions + "\n\n" + status
        view = QPlainTextEdit(self.text)
        view.setReadOnly(True)
        view.setStyleSheet("font-family: monospace;")
        buttons = QHBoxLayout()
        self.copy = QPushButton(_("📋 Copy the report"))
        self.copy.clicked.connect(self.copy_report)
        buttons.addWidget(self.copy)
        form = QPushButton(_("Open the form on GitHub"))
        form.setObjectName("apply")
        form.clicked.connect(lambda: follow_link(works_form_url(versions, status)))
        buttons.addWidget(form)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        lay.addWidget(view, 1)

    def copy_report(self):
        QApplication.clipboard().setText(self.text)
        self.copy.setText(_("📋 Copied"))
