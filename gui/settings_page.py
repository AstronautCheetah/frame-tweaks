"""The installer window's ⚙ Settings page of a tweak (lib/sft.py SETTINGS: the same choices as
./install.sh settings and the gears in VR): its options, Reset, and its actions, which run in the
background."""
import json
import os
import re

from PyQt6 import sip
from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget)

import sft  # (lib/ is on the path)
from sft import components
from i18n import _  # (translations: locale/README.md)


def action_command(a):
    """A settings action's command (a: one of its manifest's settings: actions)."""
    return ["bash", str(a["dir"] / a["script"]), *a.get("args", [])]


def running_action(window):
    """The settings action running in the background, or None (one at a time: SettingsSection.act)."""
    return next((p for p in window.findChildren(QProcess, "action")
                 if p.state() != QProcess.ProcessState.NotRunning), None)


def action_said(proc):
    """How a settings action that ended went: its last line of output, or "Didn't work: …" with it."""
    lines = [re.sub(r"\x1b\[[0-9;]*m", "", l).strip() for l in
             bytes(proc.readAll()).decode(errors="replace").splitlines()]
    lines = [l for l in lines if l and "#" not in l[:3]]          # (not curl's progress bar)
    ok = proc.exitStatus() == QProcess.ExitStatus.NormalExit and proc.exitCode() == 0
    last = lines[-1] if lines else _("Done.")
    return last if ok else _("Didn't work: %s") % last


LONG_CHOICE = 28        # (a settings choice with a longer label gets a row of its own)


class SettingsSection(QWidget):
    """One tweak's settings (lib/sft.py SETTINGS: the same choices as ./install.sh settings and the
    gears in VR): its options, Reset, and its action buttons. notice: where it reports."""

    def __init__(self, cid, notice):
        super().__init__()
        self.cid, self.spec, self.notice = cid, sft.SETTINGS[cid], notice
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        about = QLabel(self.spec["about"])
        about.setObjectName("desc")
        about.setWordWrap(True)
        lay.addWidget(about)
        self.conf = sft.read_settings(cid)
        self.buttons, self.checks = {}, {}
        for key, label, choices, _default in self.spec["options"]:
            if key in self.spec["checkboxes"]:          # on / off: one tick box
                box = QCheckBox(label)
                box.setStyleSheet("font-weight: 600; margin-top: 14px;")
                box.setChecked(self.conf.get(key) == choices[0][1])
                box.clicked.connect(lambda on, k=key, c=choices: self.choose(k, c[0][1] if on else c[1][1]))
                lay.addWidget(box)
                self.checks[key] = (box, choices[0][1])
                continue
            lab = QLabel(label)
            lab.setStyleSheet("font-weight: 600; margin-top: 14px;")
            lay.addWidget(lab)
            grid = QGridLayout()                     # (wraps: a long list of choices fits the page)
            longest = max((len(t) for t, _value in choices), default=0)
            # (Long labels one per row: four of them side by side, each as wide as its text, made
            # the page wider than the window and pushed buttons off its edge.)
            per_row = 7 if longest <= 8 else 4 if longest <= LONG_CHOICE else 1
            swatches = key in self.spec["swatches"]
            if swatches:                             # circles of colour, as the gear's panel in VR
                per_row = 12
            row, group = 0, None
            for n, (text, value) in enumerate(choices):
                b = QPushButton(text)
                b.setCheckable(True)
                b.setChecked(self.conf.get(key) == value)
                bold = QFont(b.font())
                bold.setBold(True)                   # (wide enough for the chosen one's bold text,
                bold.setPixelSize(15)                # at STYLE's 14 px, measured before it applies)
                b.setMinimumWidth(max(70, QFontMetrics(bold).horizontalAdvance(text) + 36))
                b.setStyleSheet("QPushButton:checked { background: #355b7a; font-weight: 600; }")
                if swatches and isinstance(value, (int, float)):
                    hue = round(value * 360)
                    b.setText("")
                    b.setToolTip(text)
                    b.setAccessibleName(text)
                    b.setFixedSize(44, 44)
                    b.setMinimumWidth(44)
                    b.setStyleSheet(f"QPushButton {{ background: hsl({hue}, 60%, 55%); border-radius: 22px;"
                                    f" border: 2px solid rgba(255, 255, 255, 64); padding: 0; }}"
                                    f" QPushButton:checked {{ border: 4px solid white; }}")
                b.clicked.connect(lambda _=False, k=key, v=value: self.choose(k, v))
                if per_row == 1:                     # (a gap where "Recommended: …" turns into "Not recommended: …")
                    head = text.split(": ", 1)[0] if ": " in text else None
                    if group is not None and head != group:
                        grid.setRowMinimumHeight(row, 10)
                        row += 1
                    group = head
                    b.setMinimumWidth(0)
                    b.setStyleSheet(b.styleSheet() + " QPushButton { text-align: left; padding-left: 14px; }")
                    grid.addWidget(b, row, 0)
                    row += 1
                else:
                    grid.addWidget(b, n // per_row, n % per_row)
                self.buttons[(key, text)] = (b, value)
            grid.setColumnStretch(per_row if per_row > 1 else 0, 1)
            lay.addLayout(grid)
        reset = QPushButton(_("Reset to defaults"))
        reset.clicked.connect(self.reset)
        lay.addWidget(reset)
        self.actions = []
        for a in self.spec["actions"]:
            b = QPushButton()
            b.clicked.connect(lambda _=False, a=a: self.act(a))
            note = QLabel(a.get("about", ""))
            note.setObjectName("desc")
            note.setWordWrap(True)
            row = QHBoxLayout()
            row.addWidget(b)
            row.addWidget(note, 1)
            lay.addSpacing(10)
            lay.addLayout(row)
            self.actions.append((a, b, note))
        self.commands = {"\0".join(action_command(a)) for a in self.spec["actions"]}
        self.show_actions()

    def show_actions(self):
        for a, b, note in self.actions:
            value = sft.raw_setting(self.cid, a["when"]) if a.get("when") else ""
            b.setText(re.sub(r"\{(\w+)\}", lambda m: sft.raw_setting(self.cid, m[1]), a["label"]))
            b.setVisible(not a.get("when") or bool(value))
            note.setVisible(b.isVisibleTo(self) or not a.get("when"))

    def act(self, a):
        """Run the action's script in the background (a download can take a while); its last line
        of output says how it went. It's the window's process (going Back mustn't stop it), so
        one at a time: a page opened again meanwhile doesn't start a second, but says how the one
        running goes."""
        cmd = action_command(a)
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would run:", " ".join(cmd))
            return
        running = running_action(self.window())
        if running is not None and running.property("command") != "\0".join(cmd):
            self.notice.setText(_("Another action is still running: try again once it's done."))
            return
        if running is None:
            running = QProcess(self.window())
            running.setObjectName("action")
            running.setProperty("command", "\0".join(cmd))       # (what a page opened again looks for)
            running.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            running.finished.connect(lambda *_args, p=running: (p.setProperty("said", action_said(p)), p.deleteLater()))
            running.start(cmd[0], cmd[1:])
        self.follow(running)

    def follow(self, proc):
        """Working… on this section's page until proc, its action, ends (started here, or from a
        page closed since); then how it went (action_said)."""
        self.notice.setText(_("Working… (a download can take a minute)"))
        for _a, b, _note in self.actions:
            b.setEnabled(False)

        def done(*_args):
            if sip.isdeleted(self):             # (its page was closed meanwhile)
                return
            self.notice.setText(proc.property("said") or _("Done."))
            for _a, b, _note in self.actions:
                b.setEnabled(True)
            self.show_actions()
        proc.finished.connect(done)

    def show_choices(self):
        for (key, _text), (b, value) in self.buttons.items():
            b.setChecked(self.conf.get(key) == value)
        for key, (box, on) in self.checks.items():
            box.setChecked(self.conf.get(key) == on)

    def choose(self, key, value):
        self.conf[key] = value
        self.show_choices()
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would save:", self.cid, json.dumps({key: value}))
            return
        sft.write_settings(self.cid, {key: value})
        self.notice.setText(_("Saved.") + " " + self.spec["note"])

    def reset(self):
        self.conf = sft.defaults(self.cid)
        self.show_choices()
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):
            print("would reset:", self.cid)
            return
        sft.write_settings(self.cid, {}, reset=True)
        self.notice.setText(_("Back to the defaults.") + " " + self.spec["note"])


class SettingsPage(QWidget):
    """A tweak's settings page: its own section, then those of the tweaks its settings include
    (Screen snip + Narrate shows the Speech engine's: same files, same choices)."""

    def __init__(self, window, cid):
        super().__init__()
        self.cid = cid
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        back = QPushButton(_("← Back"))
        back.clicked.connect(window.go_back)
        head.addWidget(back)
        title = QLabel(next((c["title"] for c in components() if c["id"] == cid), cid))
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)
        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 8, 0)
        self.sections = [SettingsSection(cid, self.notice)]
        col.addWidget(self.sections[0])
        for other in sft.SETTINGS[cid]["include"]:
            if other not in sft.SETTINGS:
                continue
            head2 = QLabel(next((c["title"] for c in components() if c["id"] == other), other))
            head2.setObjectName("title")
            head2.setStyleSheet("margin-top: 22px;")
            col.addWidget(head2)
            self.sections.append(SettingsSection(other, self.notice))
            col.addWidget(self.sections[-1])
        col.addStretch(1)
        running = running_action(window)         # (one of its actions, started from this page closed since)
        for section in self.sections:
            if running is not None and running.property("command") in section.commands:
                section.follow(running)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        lay.addWidget(scroll, 1)
        lay.addWidget(self.notice)


SETTINGS_PAGES = {cid: (lambda w, c=cid: SettingsPage(w, c)) for cid in sft.SETTINGS}   # the row's button opens these
