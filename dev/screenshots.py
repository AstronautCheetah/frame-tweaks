#!/usr/bin/env python3
"""Screenshots of the Core tweaks' windows for the README (docs/images/), drawn off-screen with
sample content: a throwaway home, so nothing of this machine's (its settings, apps, files or
wallet) shows, and they can be taken again whenever a window changes.

  ~/.local/share/arrowpad/venv/bin/python dev/screenshots.py [NAME...]    (a Python with PyQt6)

NAME: arrowpad, arrowpad-tools, snip, narrate, wallet (default: all). Views that only exist in VR
(Android Mirror's ⚙, the scroll strips) are taken in the headset instead."""
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/images"
HOME = Path(tempfile.mkdtemp(prefix="ft-screenshots-"))
# (before anything reads them: the programs look for their settings in this home)
os.environ.update({"HOME": str(HOME), "QT_QPA_PLATFORM": "offscreen", "FRAME_TWEAKS_LANGUAGE": "en",
                   "FRAME_TWEAKS_KEYBOARD": "0", "FRAME_TWEAKS_PYLIB": str(ROOT / "lib"),
                   "FRAME_TWEAKS_PREFERENCE_FILE": str(HOME / "language"),
                   "FRAME_TWEAKS_ANNOUNCE_FILE": str(HOME / "announced-language"),
                   "FRAME_TWEAKS_DRY_RUN": "1", "FRAME_TWEAKS_PACKS": ""})
os.environ.pop("DISPLAY", None)
sys.modules["openvr"] = None                     # (no SteamVR: the desktop versions of the windows)
sys.path.insert(0, str(ROOT / "lib"))

from PyQt6.QtCore import QObject, QRect, Qt, QTimer, pyqtSignal  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

APP = QApplication.instance() or QApplication(sys.argv)
# What the snip and Narrate show: a paragraph of Frame Tweaks' own README.
PARAGRAPH = ("The Frame runs a full KDE Plasma desktop, but out of the box it is awkward to use from the "
             "headset. Steam's on-screen keyboard has no up/down arrows, Esc, Ctrl or F-keys, and pointing "
             "at keys with a laser is slow. Desktop mode and VR are two separate sessions, each with its own "
             "clipboard and its own KDE wallet.")


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


def settle(seconds=0.6):
    end = time.time() + seconds
    while time.time() < end:
        APP.processEvents()
        time.sleep(0.02)


def save(widget, name):
    widget.show()
    settle()
    widget.grab().save(str(OUT / f"{name}.png"))
    print(f"docs/images/{name}.png  {widget.width()}x{widget.height()}")


class Keys:
    """Arrow Pad's typing (ydotool), doing nothing."""
    def key(self, code, down):
        pass

    def tap(self, *codes):
        pass

    def clear_stuck_modifiers(self):
        pass


def arrowpad(tools=False):
    ap = load("arrowpad", ROOT / "packs/core/arrowpad/arrowpad.py")
    ap.CONFIG, ap.Haptics = HOME / "arrowpad.json", None
    pad = ap.ArrowPad(Keys(), None)
    if tools:
        pad.layer = "tools"
        pad.relabel()
    save(pad, "arrowpad-tools" if tools else "arrowpad")


def sample_screen(w=1280, h=720):
    """A desktop with a page of text on it: what the snip is taken of."""
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(QColor("#1b2836"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    page = QRect(150, 70, w - 300, h - 140)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#f4f5f7"))
    p.drawRoundedRect(page, 10, 10)
    p.setBrush(QColor("#dfe3e8"))
    p.drawRoundedRect(QRect(page.x(), page.y(), page.width(), 44), 10, 10)
    p.setPen(QColor("#1f2933"))
    p.setFont(QFont("Noto Sans", 13))
    p.drawText(QRect(page.x() + 20, page.y(), page.width(), 44), Qt.AlignmentFlag.AlignVCenter, "README.md")
    p.setFont(QFont("Noto Sans", 26, QFont.Weight.Bold))
    p.drawText(QRect(page.x() + 60, page.y() + 80, page.width() - 120, 50), 0, "Why")
    p.setFont(QFont("Noto Sans", 17))
    p.drawText(QRect(page.x() + 60, page.y() + 150, page.width() - 120, 260), Qt.TextFlag.TextWordWrap, PARAGRAPH)
    p.end()
    return img


def snip_module():
    return load("frame_snip", ROOT / "packs/core/snip/frame-snip")


def snip():
    fs = snip_module()
    s = fs.Snip(sample_screen())
    s.sel = QRect(185, 212, 905, 153)            # around the paragraph, as a laser would draw it
    s.resize(s.pix.size())
    s.show()
    settle(0.2)
    s.place_bar()
    save(s, "snip")


def narrate():
    fs = snip_module()

    class Quiet(QObject):
        """The narrator, silent: says it's reading part 2 of 3."""
        progress, finished = pyqtSignal(int, int), pyqtSignal()
        paused = stopped = False

        def __init__(self, text, speed):
            super().__init__()

        def start(self):
            QTimer.singleShot(0, lambda: self.progress.emit(1, 3))

        def __getattr__(self, name):              # (pause, resume, cleanup…: nothing to do)
            return lambda *a, **k: None
    fs.Narrator = Quiet
    w = fs.NarrationWindow(sample_screen().copy(185, 212, 905, 153), PARAGRAPH, fs.load_speed(), panel=True)
    save(w, "narrate")


def wallet():
    """The installer window's Wallet apps page, with three apps behind the wallet."""
    bin_dir = HOME / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    info = {"state": "unlocked", "unlocked_at": now - 25 * 60, "locks_at": now + 4 * 3600 - 25 * 60, "autolock": True}
    for name, body in (("wallet-unlock", f"echo '{json.dumps(info)}'"), ("app-timers", "printf 'org.signal.Signal 15 headset\\n'"),
                       ("wallet-launcher", "exit 0")):
        (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n")
        (bin_dir / name).chmod(0o755)
    apps = HOME / ".local/share/applications"
    apps.mkdir(parents=True, exist_ok=True)
    flatpak = "/usr/bin/flatpak run"
    for app_id, name, gate, electron in (("org.signal.Signal", "Signal", True, True),
                                          ("com.vscodium.codium", "VSCodium", False, True),
                                          ("org.mozilla.firefox", "Firefox", True, False)):
        exec_ = (f"{HOME}/.local/bin/frame-outer-bus " + (f"{HOME}/.local/bin/wallet-gate " if gate else "")
                 + f"{flatpak} {app_id}" + (" --password-store=kwallet6" if electron else ""))
        (apps / f"{app_id}.desktop").write_text(f"[Desktop Entry]\nType=Application\nName={name}\nIcon={app_id}\n"
                                                f"Exec={exec_}\nX-FrameTweaks-Wallet=true\n")
    gui = load("gui", ROOT / "gui/frame-tweaks-gui.py")
    gui.sft.build_version = lambda: gui.current_release()
    win = gui.Window()
    win.resize(1000, 700)
    win.show()
    settle()
    win.run(gui.component("wallet"))
    save(win, "wallet")


VIEWS = {"arrowpad": arrowpad, "arrowpad-tools": lambda: arrowpad(tools=True), "snip": snip,
         "narrate": narrate, "wallet": wallet}

if __name__ == "__main__":
    names = sys.argv[1:] or list(VIEWS)
    bad = [n for n in names if n not in VIEWS]
    if bad:
        sys.exit(f"unknown: {' '.join(bad)} (one of: {' '.join(VIEWS)})")
    OUT.mkdir(parents=True, exist_ok=True)
    for n in names:
        VIEWS[n]()
