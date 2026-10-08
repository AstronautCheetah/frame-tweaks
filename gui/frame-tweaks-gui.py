#!/usr/bin/env python3
"""Steam Frame Tweaks: graphical installer.

One row per tweak: tick to install, untick to remove, see its health, and hide rows you
don't care about (hidden tweaks are only hidden, never removed). "Show hidden" brings
them back. Changes run in a Konsole window via ./install.sh, as from the command line.
Styled after Full Keyboard's Graphite theme, like Arrow Pad.
"""
import os
import shlex
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel,
                             QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget)

REPO = Path(__file__).resolve().parent.parent
HIDDEN = Path.home() / ".config/steam-frame-tweaks/hidden"
ICONS = Path.home() / ".local/share/icons/hicolor/256x256/apps"
BREEZE = Path("/usr/share/icons/breeze-dark")
# Icons for rows: our own menu icons where a tweak has one, else a Breeze glyph.
ROW_ICON = {"dictation": "frame-tweaks-dictate", "arrowpad": "frame-tweaks-arrowpad",
            "adb-scrcpy": "frame-tweaks-phone", "nordvpn": "frame-tweaks-nordvpn",
            "wallet": "frame-tweaks-lock"}
FLATPAK_ICONS = Path("/var/lib/flatpak/exports/share/icons/hicolor")
FLATPAK_ROW = {"vscodium": "com.vscodium.codium", "signal": "org.signal.Signal",
               "firefox": "org.mozilla.firefox"}
BREEZE_ROW = {"whisper-frame": "audio-input-microphone", "clipboard": "edit-paste",
              "full-keyboard": "input-keyboard", "cursor": "input-mouse", "signal": "dialog-messages",
              "firefox": "internet-web-browser", "claude-desktop": "help-about",
              "tools": "tools", "ydotool": "input-keyboard-virtual"}

STYLE = """
QWidget { background: #0b1016; color: #e8ecf0; font-size: 14px; }
QLabel#title { font-size: 20px; font-weight: 600; }
QLabel#name { font-size: 15px; font-weight: 600; }
QLabel#desc { color: #9aa6b2; }
QLabel[status="ok"] { color: #5cc77a; } QLabel[status="warn"] { color: #e0b33a; }
QLabel[status="missing"] { color: #6b7783; }
QWidget#row { background: #161c23; border-radius: 10px; }
QWidget#row[hidden_row="true"] { background: #11161c; }
QWidget#row QLabel, QWidget#row QCheckBox { background: transparent; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2c333b, stop:0.5 #232a32, stop:1 #1c232a);
              border: none; border-bottom: 3px solid #0c1015; border-radius: 8px; padding: 6px 14px; }
QPushButton:hover { background: #3d4855; }
QPushButton:checked { background: #355b7a; }
QPushButton#apply { background: #355b7a; font-weight: 600; }
QCheckBox::indicator { width: 22px; height: 22px; }
QScrollArea { border: none; }
"""


def components():
    rows = []
    for line in (REPO / "components.tsv").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cid, title, deps, desc, source = (line.split("\t") + ["", "", "", "", ""])[:5]
        rows.append((cid, title, deps.split(), desc, source))
    return rows


def status(cid):
    """(code, text): 0 ok, 1 not installed, 2 needs attention."""
    r = subprocess.run([str(REPO / cid / "status.sh")], capture_output=True, text=True)
    text = r.stdout.strip().split(None, 1)[-1] if r.stdout.strip() else ""
    return r.returncode, text


def load_hidden():
    try:
        return set(HIDDEN.read_text().split())
    except OSError:
        return set()


def save_hidden(hidden):
    HIDDEN.parent.mkdir(parents=True, exist_ok=True)
    HIDDEN.write_text("".join(f"{h}\n" for h in sorted(hidden)))


def row_icon(cid):
    if cid in FLATPAK_ROW:   # the app's own icon, as Flathub exports it
        hits = sorted(FLATPAK_ICONS.glob(f"*/apps/{FLATPAK_ROW[cid]}.*"),
                      key=lambda p: (p.suffix == ".svg", p.parent.parent.name))
        if hits:
            return QIcon(str(hits[-1]))
    if cid in ROW_ICON and (ICONS / f"{ROW_ICON[cid]}.png").exists():
        return QIcon(str(ICONS / f"{ROW_ICON[cid]}.png"))
    hits = sorted(BREEZE.glob(f"*/*/{BREEZE_ROW.get(cid, 'application-x-executable')}.svg"))
    return QIcon(str(hits[-1])) if hits else QIcon()


class Window(QWidget):
    def __init__(self):
        super().__init__()
        version = (REPO / "VERSION").read_text().strip() if (REPO / "VERSION").exists() else ""
        self.setWindowTitle(f"Steam Frame Tweaks {version}")
        icon = ICONS / "frame-tweaks.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.setStyleSheet(STYLE)
        self.resize(980, 720)
        self.hidden = load_hidden()
        self.rows = components()
        self.state = {}       # cid -> (status code, text)
        self.boxes = {}

        top = QHBoxLayout()
        title = QLabel(f"Steam Frame Tweaks <span style='color:#6b7783;font-size:14px'>{version}</span>")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch(1)
        self.show_hidden = QPushButton()
        self.show_hidden.setCheckable(True)
        self.show_hidden.toggled.connect(self.rebuild)
        top.addWidget(self.show_hidden)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        top.addWidget(refresh)

        self.list = QWidget()
        self.grid = QVBoxLayout(self.list)
        self.grid.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.list)

        bottom = QHBoxLayout()
        hint = QLabel("Tick to install, untick to remove. Hidden tweaks are only hidden, never removed.")
        hint.setObjectName("desc")
        bottom.addWidget(hint)
        bottom.addStretch(1)
        apply_ = QPushButton("Apply changes")
        apply_.setObjectName("apply")
        apply_.clicked.connect(self.apply)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        bottom.addWidget(apply_)
        bottom.addWidget(close)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.addLayout(top)
        outer.addWidget(scroll, 1)
        outer.addLayout(bottom)
        self.refresh()

    def refresh(self):
        self.state = {cid: status(cid) for cid, *_ in self.rows}
        self.rebuild()

    def rebuild(self, *_):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        n_hidden = sum(1 for cid, *_ in self.rows if cid in self.hidden)
        self.show_hidden.setText(f"Show hidden ({n_hidden})")
        self.show_hidden.setEnabled(n_hidden > 0 or self.show_hidden.isChecked())
        old = {cid: b.isChecked() for cid, b in self.boxes.items()}
        self.boxes = {}
        for cid, title, deps, desc, source in self.rows:
            hidden = cid in self.hidden
            if hidden and not self.show_hidden.isChecked():
                continue
            code, text = self.state.get(cid, (1, ""))
            row = QWidget()
            row.setObjectName("row")
            row.setProperty("hidden_row", "true" if hidden else "false")
            g = QGridLayout(row)
            g.setContentsMargins(12, 10, 12, 10)
            g.setHorizontalSpacing(14)
            box = QCheckBox()
            box.setChecked(old.get(cid, code != 1))
            box.setToolTip("Installed" if code != 1 else "Not installed")
            self.boxes[cid] = box
            icon = QLabel()
            icon.setPixmap(row_icon(cid).pixmap(40, 40))
            name = QLabel(title + ("  <span style='color:#6b7783'>(hidden)</span>" if hidden else ""))
            name.setObjectName("name")
            info = QLabel(desc + (f"  <i style='color:#6b7783'>needs: {', '.join(deps)}</i>" if deps else ""))
            info.setObjectName("desc")
            info.setWordWrap(True)
            link = QLabel()
            if "|" in source:     # credit the project it comes from, with a link to it
                rel, url = source.split("|", 1)
                short = url.split("://", 1)[-1].removeprefix("github.com/").rstrip("/")
                link.setText(f"<span style='color:#6b7783'>{rel}</span> "
                             f"<a style='color:#7fb2e5' href='{url}'>{short} ↗</a>")
                link.setOpenExternalLinks(True)
                link.setToolTip(f"Open {url}")
            st = QLabel({0: "✔ " + text, 2: "! " + text}.get(code, "· not installed"))
            st.setProperty("status", {0: "ok", 2: "warn"}.get(code, "missing"))
            st.setWordWrap(True)
            hide = QPushButton("Unhide" if hidden else "Hide")
            hide.setToolTip("Show this tweak in the list again" if hidden else
                            "Hide this tweak from the list (doesn't remove it)")
            hide.clicked.connect(lambda _=False, c=cid: self.toggle_hidden(c))
            g.addWidget(box, 0, 0, 3, 1)
            g.addWidget(icon, 0, 1, 3, 1)
            g.addWidget(name, 0, 2)
            g.addWidget(info, 1, 2)
            if link.text():
                g.addWidget(link, 2, 2)
            g.addWidget(st, 0, 3, 3, 1)
            g.addWidget(hide, 0, 4, 3, 1)
            g.setColumnStretch(2, 3)
            g.setColumnStretch(3, 2)
            self.grid.addWidget(row)
        self.grid.addStretch(1)

    def toggle_hidden(self, cid):
        self.hidden ^= {cid}
        save_hidden(self.hidden)
        self.rebuild()

    def apply(self):
        add = [cid for cid, b in self.boxes.items() if b.isChecked() and self.state[cid][0] != 0]
        remove = [cid for cid, b in self.boxes.items() if not b.isChecked() and self.state[cid][0] != 1]
        if not add and not remove:
            QMessageBox.information(self, "Steam Frame Tweaks", "Nothing to change.")
            return
        if remove:
            msg = ("These installed tweaks were unticked and will be REMOVED:\n\n  "
                   + ", ".join(remove) + "\n\nTheir settings and data are kept. Continue?")
            if QMessageBox.warning(self, "Remove tweaks?", msg,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                remove = []
        if not add and not remove:
            return
        if os.environ.get("FRAME_TWEAKS_DRY_RUN"):      # for tests: show the plan, change nothing
            print("would remove:", " ".join(remove) or "none")
            print("would install:", " ".join(add) or "none")
            return
        steps = [f"cd {shlex.quote(str(REPO))}"]
        if remove:
            steps.append("./install.sh uninstall " + " ".join(remove))
        if add:
            steps.append("./install.sh install " + " ".join(add))
        cmd = " && ".join(steps) + "; echo; read -rp 'Press Enter to close…'"
        self.proc = QProcess(self)            # don't block the window while Konsole runs
        self.proc.finished.connect(lambda *_: self.refresh())
        self.proc.start("konsole", ["--separate", "-e", "bash", "-c", cmd])


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("steam-frame-tweaks")
    app.setDesktopFileName("steam-frame-tweaks")
    w = Window()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
