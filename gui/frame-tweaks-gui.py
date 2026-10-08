#!/usr/bin/env python3
"""Steam Frame Tweaks: graphical installer.

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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import QCursor, QIcon
from PyQt6.QtWidgets import (QApplication, QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
                             QMessageBox, QPushButton, QScrollArea, QTextBrowser, QVBoxLayout,
                             QWidget)

REPO = Path(__file__).resolve().parent.parent
CONF = Path.home() / ".config/steam-frame-tweaks"
HIDDEN, SHOWN = CONF / "hidden", CONF / "shown"     # SHOWN: default-hidden rows you unhid
GITHUB = "https://github.com/AstronautCheetah/steam-frame-tweaks/tree/main"
ICONS = Path.home() / ".local/share/icons/hicolor/256x256/apps"
BREEZE = Path("/usr/share/icons/breeze-dark")
FLATPAK_ICONS = Path("/var/lib/flatpak/exports/share/icons/hicolor")
ROW_ICON = {"dictation": "frame-tweaks-dictate", "arrowpad": "frame-tweaks-arrowpad",
            "adb-scrcpy": "frame-tweaks-phone", "nordvpn": "frame-tweaks-nordvpn",
            "wallet": "frame-tweaks-lock"}
FLATPAK_ROW = {"vscodium": "com.vscodium.codium", "signal": "org.signal.Signal",
               "firefox": "org.mozilla.firefox"}
BREEZE_ROW = {"whisper-frame": "audio-input-microphone", "clipboard": "edit-paste",
              "full-keyboard": "input-keyboard", "cursor": "input-mouse", "signal": "dialog-messages",
              "firefox": "internet-web-browser", "claude-desktop": "help-about",
              "tools": "tools", "ydotool": "input-keyboard-virtual"}

STYLE = """
QWidget { background: #0b1016; color: #e8ecf0; font-size: 14px; }
QLabel#title { font-size: 20px; font-weight: 600; }
QLabel#category { font-size: 13px; font-weight: 700; color: #7fb2e5; letter-spacing: 1px;
                  padding: 10px 4px 2px 4px; }
QLabel#name { font-size: 15px; font-weight: 600; }
QLabel#desc { color: #9aa6b2; }
QLabel[status="ok"] { color: #5cc77a; } QLabel[status="warn"] { color: #e0b33a; }
QLabel[status="missing"], QLabel[status="checking"] { color: #6b7783; }
QWidget#row { background: #161c23; border-radius: 10px; }
QWidget#row:hover { background: #1c242d; }
QWidget#row[hidden_row="true"] { background: #11161c; }
QWidget#row QLabel, QWidget#row QCheckBox { background: transparent; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2c333b, stop:0.5 #232a32, stop:1 #1c232a);
              border: none; border-bottom: 3px solid #0c1015; border-radius: 8px; padding: 6px 14px; }
QPushButton:hover { background: #3d4855; }
QPushButton:checked { background: #355b7a; }
QPushButton#apply { background: #355b7a; font-weight: 600; }
QPushButton#info { padding: 6px 10px; }
QCheckBox { padding: 8px; }
QCheckBox::indicator { width: 33px; height: 33px; }
QScrollArea { border: none; }
QTextBrowser { background: #11161c; border: none; border-radius: 8px; padding: 8px; }
"""


def components():
    rows = []
    for line in (REPO / "components.tsv").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = (line.split("\t") + [""] * 9)[:9]
        cid, title, category, deps, desc, source, author, why, flags = f
        rows.append(dict(id=cid, title=title, category=category, deps=deps.split(), desc=desc,
                         source=source, author=author, why=why, flags=set(flags.split(","))))
    return rows


def status(cid):
    """(code, text): 0 ok, 1 not installed, 2 needs attention."""
    r = subprocess.run([str(REPO / cid / "status.sh")], capture_output=True, text=True)
    text = r.stdout.strip().split(None, 1)[-1] if r.stdout.strip() else ""
    return r.returncode, text


def read_set(path):
    try:
        return set(path.read_text().split())
    except OSError:
        return set()


def write_set(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{i}\n" for i in sorted(items)))


def row_icon(cid):
    if cid in FLATPAK_ROW:
        hits = sorted(FLATPAK_ICONS.glob(f"*/apps/{FLATPAK_ROW[cid]}.*"),
                      key=lambda p: (p.suffix == ".svg", p.parent.parent.name))
        if hits:
            return QIcon(str(hits[-1]))
    if cid in ROW_ICON and (ICONS / f"{ROW_ICON[cid]}.png").exists():
        return QIcon(str(ICONS / f"{ROW_ICON[cid]}.png"))
    hits = sorted(BREEZE.glob(f"*/*/{BREEZE_ROW.get(cid, 'application-x-executable')}.svg"))
    return QIcon(str(hits[-1])) if hits else QIcon()


def status_text(code_text):
    if code_text is None:
        return "checking…", "checking"
    code, text = code_text
    return ({0: "✔ " + text, 2: "! " + text}.get(code, "· not installed"),
            {0: "ok", 2: "warn"}.get(code, "missing"))


class Row(QWidget):
    """Clicking anywhere on the row (but its checkbox, buttons or link) opens the details."""

    def __init__(self, window, comp):
        super().__init__()
        self.window, self.comp = window, comp
        self.setObjectName("row")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.window.show_details(self.comp)


class Details(QDialog):
    def __init__(self, parent, comp, state):
        super().__init__(parent)
        self.setWindowTitle(f"{comp['title']} — Steam Frame Tweaks")
        self.setStyleSheet(STYLE)
        self.resize(820, 720)
        lay = QVBoxLayout(self)
        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(row_icon(comp["id"]).pixmap(56, 56))
        head.addWidget(icon)
        title = QLabel(f"{html.escape(comp['title'], quote=False)}  <span style='color:#6b7783;font-size:14px'>"
                       f"{html.escape(comp['category'])}</span>")
        title.setObjectName("title")
        head.addWidget(title, 1)
        lay.addLayout(head)

        text, kind = status_text(state)
        rel, url = comp["source"].split("|", 1) if "|" in comp["source"] else ("", "")
        facts = [("What it is", html.escape(comp["desc"], quote=False)),
                 ("Why it's included", html.escape(comp["why"], quote=False)),
                 ("Made by", html.escape(comp["author"], quote=False))]
        if url:
            facts.append(("Source", f"{html.escape(rel)} <a style='color:#7fb2e5' href='{url}'>{url}</a>"))
        if comp["deps"]:
            facts.append(("Needs", ", ".join(comp["deps"]) + " (installed automatically)"))
        colour = {"ok": "#5cc77a", "warn": "#e0b33a"}.get(kind, "#9aa6b2")
        facts.append(("Status", f"<span style='color:{colour}'>{html.escape(text)}</span>"))
        facts.append(("Documentation", f"<a style='color:#7fb2e5' href='{GITHUB}/{comp['id']}'>"
                      f"{comp['id']}/README.md on GitHub</a>"))
        summary = QLabel("<table cellspacing=6>" + "".join(
            f"<tr><td style='color:#6b7783;padding-right:12px' valign=top><b>{k}</b></td><td>{v}</td></tr>"
            for k, v in facts) + "</table>")
        summary.setWordWrap(True)
        summary.setOpenExternalLinks(True)
        summary.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(summary)

        readme = QTextBrowser()
        readme.setOpenExternalLinks(True)
        readme.document().setDefaultStyleSheet(
            "a { color: #7fb2e5; } code { background: #1c232a; } pre { background: #1c232a; }")
        md = REPO / comp["id"] / "README.md"
        text = md.read_text() if md.exists() else "_No README._"
        # Links between files point at GitHub (relative ones don't resolve outside the repo).
        root = GITHUB.rsplit("/tree/", 1)[0] + "/blob/main"
        text = re.sub(r"\]\(\.\./([^)#]+)", lambda m: f"]({root}/{m.group(1)}", text)
        text = re.sub(r"\]\((?!https?:|#|mailto:)([^)]+)\)", lambda m: f"]({root}/{comp['id']}/{m.group(1)})", text)
        readme.setMarkdown(text)
        lay.addWidget(readme, 1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(close)
        lay.addLayout(bottom)


class Window(QWidget):
    def __init__(self):
        super().__init__()
        version = (REPO / "VERSION").read_text().strip() if (REPO / "VERSION").exists() else ""
        self.setWindowTitle(f"Steam Frame Tweaks {version}")
        icon = ICONS / "frame-tweaks.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))
        self.setStyleSheet(STYLE)
        self.resize(1000, 760)
        self.rows = components()
        self.state = {}               # id -> (code, text); missing = still checking
        self.boxes, self.status_labels, self.wanted = {}, {}, {}
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.futures = {}

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
        hint = QLabel("Tick to install, untick to remove, click a row for details. "
                      "Hidden tweaks are only hidden, never removed.")
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
        QTimer(self, interval=100, timeout=self.collect).start()
        self.refresh()

    # ---- hidden rows: yours, plus defaults you haven't unhidden ----------------
    def hidden(self):
        defaults = {c["id"] for c in self.rows if "hidden-by-default" in c["flags"]}
        return read_set(HIDDEN) | (defaults - read_set(SHOWN))

    def toggle_hidden(self, cid):
        hidden, shown = read_set(HIDDEN), read_set(SHOWN)
        if cid in self.hidden():
            hidden.discard(cid)
            shown.add(cid)
        else:
            hidden.add(cid)
            shown.discard(cid)
        write_set(HIDDEN, hidden)
        write_set(SHOWN, shown)
        self.rebuild()

    # ---- status, in the background ------------------------------------------------
    def refresh(self):
        self.state = {}
        self.futures = {c["id"]: self.pool.submit(status, c["id"]) for c in self.rows}
        self.rebuild()

    def collect(self):
        for cid, fut in list(self.futures.items()):
            if fut.done():
                del self.futures[cid]
                self.state[cid] = fut.result()
                if cid in self.status_labels:
                    label = self.status_labels[cid]
                    text, kind = status_text(self.state[cid])
                    label.setText(text)
                    label.setProperty("status", kind)
                    label.style().unpolish(label)
                    label.style().polish(label)
                    box = self.boxes.get(cid)
                    if box is not None and cid not in self.wanted:
                        box.blockSignals(True)
                        box.setChecked(self.state[cid][0] != 1)
                        box.blockSignals(False)

    # ---- layout -----------------------------------------------------------------
    def rebuild(self, *_):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        hidden = self.hidden()
        n_hidden = sum(1 for c in self.rows if c["id"] in hidden)
        self.show_hidden.setText(f"Show hidden ({n_hidden})")
        self.show_hidden.setEnabled(n_hidden > 0 or self.show_hidden.isChecked())
        self.boxes, self.status_labels = {}, {}
        category = None
        for comp in self.rows:
            cid = comp["id"]
            is_hidden = cid in hidden
            if is_hidden and not self.show_hidden.isChecked():
                continue
            if comp["category"] != category:
                category = comp["category"]
                head = QLabel(category.upper())
                head.setObjectName("category")
                self.grid.addWidget(head)
            row = Row(self, comp)
            row.setProperty("hidden_row", "true" if is_hidden else "false")
            g = QGridLayout(row)
            g.setContentsMargins(8, 10, 12, 10)
            g.setHorizontalSpacing(14)
            box = QCheckBox()
            state = self.state.get(cid)
            box.setChecked(self.wanted.get(cid, state[0] != 1 if state else False))
            box.setToolTip("Tick to install, untick to remove")
            box.toggled.connect(lambda on, c=cid: self.wanted.__setitem__(c, on))
            self.boxes[cid] = box
            icon = QLabel()
            icon.setPixmap(row_icon(cid).pixmap(40, 40))
            name = QLabel(html.escape(comp["title"], quote=False) +
                          ("  <span style='color:#6b7783'>(hidden)</span>" if is_hidden else ""))
            name.setObjectName("name")
            deps = comp["deps"]
            info = QLabel(html.escape(comp["desc"], quote=False) +
                          (f"  <i style='color:#6b7783'>needs: {', '.join(deps)}</i>" if deps else ""))
            info.setObjectName("desc")
            info.setWordWrap(True)
            link = QLabel()
            if "|" in comp["source"]:
                rel, url = comp["source"].split("|", 1)
                short = url.split("://", 1)[-1].removeprefix("github.com/").rstrip("/")
                link.setText(f"<span style='color:#6b7783'>{html.escape(rel)}</span> "
                             f"<a style='color:#7fb2e5' href='{url}'>{html.escape(short)} ↗</a>")
                link.setOpenExternalLinks(True)
                link.setToolTip(f"Open {url}")
            text, kind = status_text(state)
            st = QLabel(text)
            st.setProperty("status", kind)
            st.setWordWrap(True)
            self.status_labels[cid] = st
            details = QPushButton("ⓘ")
            details.setObjectName("info")
            details.setToolTip("Details: what it is, why it's included, who made it")
            details.clicked.connect(lambda _=False, c=comp: self.show_details(c))
            hide = QPushButton("Unhide" if is_hidden else "Hide")
            hide.setToolTip("Show this tweak in the list again" if is_hidden else
                            "Hide this tweak from the list (doesn't remove it)")
            hide.clicked.connect(lambda _=False, c=cid: self.toggle_hidden(c))
            g.addWidget(box, 0, 0, 3, 1)
            g.addWidget(icon, 0, 1, 3, 1)
            g.addWidget(name, 0, 2)
            g.addWidget(info, 1, 2)
            if link.text():
                g.addWidget(link, 2, 2)
            g.addWidget(st, 0, 3, 3, 1)
            g.addWidget(details, 0, 4, 3, 1)
            g.addWidget(hide, 0, 5, 3, 1)
            g.setColumnStretch(2, 3)
            g.setColumnStretch(3, 2)
            self.grid.addWidget(row)
        self.grid.addStretch(1)

    def show_details(self, comp):
        Details(self, comp, self.state.get(comp["id"])).exec()

    # ---- apply --------------------------------------------------------------
    def apply(self):
        if self.futures:
            QMessageBox.information(self, "Steam Frame Tweaks", "Still checking status; try again in a moment.")
            return
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
        self.proc.finished.connect(lambda *_: (self.wanted.clear(), self.refresh()))
        self.proc.start("konsole", ["--separate", "-e", "bash", "-c", cmd])

    def closeEvent(self, ev):
        self.pool.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(ev)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("steam-frame-tweaks")
    app.setDesktopFileName("steam-frame-tweaks")
    w = Window()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
