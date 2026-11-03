#!/usr/bin/env python3
"""Screenshots of the Core tweaks' windows for the README (docs/images/), drawn off-screen with
sample content: a throwaway home, so nothing of this machine's (its settings, apps, files or
wallet) shows, and they can be taken again whenever a window changes.

  ~/.local/share/arrowpad/venv/bin/python dev/screenshots.py [NAME...]    (a Python with PyQt6)

NAME: arrowpad, arrowpad-tools, snip, narrate, wallet, memory-limits, scroll-strips, menu-icons,
recline (default: all). Views that
only exist in VR are taken in the headset instead (Android Mirror's ⚙), or drawn: the scroll
strips, beside a generic window, as their dashboard patch draws them."""
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
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPen  # noqa: E402
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
        progress, finished, failed = pyqtSignal(int, int), pyqtSignal(), pyqtSignal(str, int)
        paused = stopped = False

        def __init__(self, text, speed, volume=1.0):
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


def memory():
    """The installer window's Memory limits page (VR memory guard): five apps, Firefox and VLC with
    a limit of their own, the others sharing the apps' pool. (vr-memory-guard-tool info, a stand-in;
    the apps' names and icons are their menu entries', where they're installed.)"""
    bin_dir = HOME / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    apps = [{"id": i, "limit": lim, "swap": 1024 if lim else None, "installed": True}
            for i, lim in (("org.mozilla.firefox", 5120), ("org.videolan.VLC", 2048), ("org.signal.Signal", None),
                           ("org.gimp.GIMP", None), ("org.kde.kate", None))]
    info = {"total": 15662, "reserve": 5120, "apps_swap": 2048, "pool": 10542, "min_reserve": 1024,
            "max_reserve": 13614, "min_limit": 256, "default_swap": 1024, "apps": apps}
    tool = bin_dir / "vr-memory-guard-tool"
    tool.write_text(f"#!/bin/sh\n[ \"$1\" = info ] && echo '{json.dumps(info)}'\nexit 0\n")
    tool.chmod(0o755)
    gui = load("gui", ROOT / "gui/frame-tweaks-gui.py")
    gui.sft.build_version = lambda: gui.current_release()
    win = gui.Window()
    win.resize(1000, 700)
    win.show()
    settle()
    win.run(gui.component("vr-memory-guard"))
    save(win, "memory-limits")


def menu_icons():
    """Menu icons (3rd Party): apps in Steam's VR "+" menu before (a blank icon: Steam looks only in
    hicolor) and after (Breeze's icon, copied there). Drawn as a plain list, not Steam's menu; the
    icons are this system's Breeze theme's (SteamOS has it)."""
    from PyQt6.QtGui import QIcon
    rows = (("Konsole", "utilities-terminal"), ("System Settings", "preferences-system"),
            ("Dolphin", "system-file-manager"), ("Discover", "plasmadiscover"))
    w, h = 900, 120 + 76 * len(rows)
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, 0, w, h, QColor("#10161d"))
    for col, (title, with_icons) in enumerate((("Before", False), ("With Menu icons", True))):
        x = 40 + col * (w // 2)
        box = QRect(x, 30, w // 2 - 80, h - 60)
        p.setPen(QColor("#2a3440"))
        p.setBrush(QColor("#1a222c"))
        p.drawRoundedRect(box, 14, 14)
        p.setPen(QColor("#9aa6b2"))
        p.setFont(QFont("Noto Sans", 15, QFont.Weight.Bold))
        p.drawText(QRect(x + 24, 44, box.width(), 30), 0, title)
        for i, (name, icon) in enumerate(rows):
            y = 90 + i * 76
            r = QRect(x + 24, y, 52, 52)
            if with_icons:                               # (by its file: off-screen, the theme isn't searched)
                p.drawPixmap(r, QIcon(f"/usr/share/icons/breeze/apps/48/{icon}.svg").pixmap(52, 52))
            else:                                        # (Steam's blank: an empty tile)
                p.setPen(QColor("#3a4654"))
                p.setBrush(QColor("#232c37"))
                p.drawRoundedRect(r, 10, 10)
            p.setPen(QColor("#e8ecf0"))
            p.setFont(QFont("Noto Sans", 17))
            p.drawText(QRect(x + 96, y, box.width() - 120, 52), Qt.AlignmentFlag.AlignVCenter, name)
    p.end()
    img.save(str(OUT / "menu-icons.png"))
    print(f"docs/images/menu-icons.png  {w}x{h}")


def recline():
    """Recline (3rd Party), as a diagram: lying back, you'd see the ceiling; recentered with Recline,
    the way you look is forward and level in VR."""
    w, h = 1100, 460
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, 0, w, h, QColor("#10161d"))
    ink, accent, dim = QColor("#e8ecf0"), QColor("#7fb2e5"), QColor("#9aa6b2")

    def person(ox, oy):
        """Someone lying back in a recliner, side on; returns where the eyes are."""
        p.setPen(QPen(QColor("#3a4654"), 14, cap=Qt.PenCapStyle.RoundCap))
        p.drawLine(ox - 150, oy + 40, ox + 40, oy + 40)          # (the seat)
        p.drawLine(ox - 150, oy + 40, ox - 230, oy - 50)         # (the back, reclined)
        p.setPen(QPen(ink, 10, cap=Qt.PenCapStyle.RoundCap))
        p.drawLine(ox - 140, oy + 20, ox - 205, oy - 45)         # (the body)
        p.drawLine(ox - 140, oy + 20, ox + 20, oy + 20)          # (the legs)
        p.setBrush(ink)
        p.drawEllipse(ox - 238, oy - 88, 40, 40)                 # (the head)
        p.setPen(QPen(accent, 6))
        p.setBrush(accent)
        p.drawRoundedRect(ox - 206, oy - 80, 16, 26, 4, 4)       # (the headset)
        return ox - 198, oy - 67

    def arrow(x1, y1, x2, y2, colour):
        import math
        p.setPen(QPen(colour, 5, cap=Qt.PenCapStyle.RoundCap))
        p.drawLine(x1, y1, x2, y2)
        a = math.atan2(y2 - y1, x2 - x1)
        for d in (2.6, -2.6):
            p.drawLine(x2, y2, int(x2 + 18 * math.cos(a + d)), int(y2 + 18 * math.sin(a + d)))

    p.setFont(QFont("Noto Sans", 18, QFont.Weight.Bold))
    for col, (title, note) in enumerate((("Lying back", "You look at the ceiling: in VR, the sky"),
                                         ("Recentered with Recline", "That way is forward and level in VR"))):
        x0 = col * (w // 2)
        p.setPen(ink)
        p.setFont(QFont("Noto Sans", 18, QFont.Weight.Bold))
        p.drawText(QRect(x0 + 40, 30, w // 2 - 60, 34), 0, title)
        p.setPen(dim)
        p.setFont(QFont("Noto Sans", 15))
        p.drawText(QRect(x0 + 40, 66, w // 2 - 60, 30), 0, note)
        ex, ey = person(x0 + 330, 330)
        arrow(ex, ey, ex + 90, ey - 150, accent)                 # (where you look: up and ahead)
        # the view in VR: a horizon, tilted (looking up) or level
        v = QRect(x0 + 300, 130, 220, 130)
        p.setPen(QPen(QColor("#2a3440"), 2))
        p.setBrush(QColor("#1a222c"))
        p.drawRoundedRect(v, 10, 10)
        p.setPen(QPen(accent if col else dim, 3))
        if col:
            p.drawLine(v.x() + 14, v.center().y(), v.right() - 14, v.center().y())
            p.setPen(ink)
            p.drawText(v.adjusted(0, 0, 0, -8), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, "horizon, ahead")
        else:
            p.drawLine(v.x() + 14, v.bottom() - 10, v.right() - 14, v.bottom() - 10)
            p.setPen(ink)
            p.drawText(v.adjusted(0, 8, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "sky")
    p.end()
    img.save(str(OUT / "recline.png"))
    print(f"docs/images/recline.png  {w}x{h}")


def hsla(h, s, l, a=1.0):
    c = QColor.fromHslF(h / 360, s / 100, l / 100)
    c.setAlphaF(a)
    return c


def scroll_strips():
    """The scroll strips beside a generic window floating in VR: drawn here with the colours and
    proportions of their patch (packs/core/scroll-strips/patch.js colors(), DEFAULTS: right and
    top, 4 cm thick, 1.5 cm from the window, the passthrough tint's blue), the right one held
    (where it was pressed, and where the laser is now), and the gear where the two would meet.
    (In the headset, a screenshot would show whatever windows were open.)"""
    w, h, hue = 1240, 700, 210
    cm = 1000 / 120                      # (the window: 120 cm wide, 1000 px here)
    thick, gap = round(4 * cm), round(1.5 * cm)
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(0, 0, w, h, QColor("#10161d"))            # (VR's dark surroundings)
    win = QRect(70, 70, 1000, 600)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#f4f5f7"))
    p.drawRoundedRect(win, 12, 12)
    p.setBrush(QColor("#dfe3e8"))
    p.drawRoundedRect(QRect(win.x(), win.y(), win.width(), 46), 12, 12)
    p.setPen(QColor("#1f2933"))
    p.setFont(QFont("Noto Sans", 14))
    p.drawText(QRect(win.x() + 22, win.y(), win.width(), 46), Qt.AlignmentFlag.AlignVCenter, "Document")
    p.setFont(QFont("Noto Sans", 17))
    p.drawText(QRect(win.x() + 50, win.y() + 76, win.width() - 100, 150), Qt.TextFlag.TextWordWrap, PARAGRAPH)
    p.setPen(Qt.PenStyle.NoPen)                          # (more of the page: lines of text, unreadable)
    p.setBrush(QColor("#d3d8de"))
    y = win.y() + 250
    for n in range(9):
        if n % 4 != 3:                                   # (a gap between paragraphs)
            p.drawRoundedRect(win.x() + 50, y, win.width() - 100 - (260 if n % 4 == 2 else 0), 14, 7, 7)
        y += 34

    def strip(rect, held=None):
        """One strip (patch.js stripsFor): rounded, its border in the hue; held: (pressed, now) along it."""
        p.setPen(hsla(hue, 60, 68, 0.65))
        p.setBrush(hsla(hue, 45, 34, 0.85) if held else hsla(hue, 18, 20, 0.6))
        r = min(rect.width(), rect.height()) / 2
        p.drawRoundedRect(rect, r, r)
        if held:
            cx = rect.center().x()
            for at, size, colour in ((held[0], 10, QColor(232, 236, 240, 89)), (held[1], 14, hsla(hue, 65, 68))):
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(colour)
                p.drawEllipse(cx - size // 2, rect.y() + at - size // 2, size, size)
    right = QRect(win.right() + gap, win.y(), thick, win.height())
    top = QRect(win.x(), win.y() - gap - thick, win.width(), thick)
    strip(top)
    strip(right, held=(240, 330))                    # (pressed at 240, dragged down: scrolling down)
    # the gear, where the two strips meet (patch.js gearFor)
    g = QRect(right.x() - 4, top.y() - 4, thick + 8, thick + 8)
    p.setPen(hsla(hue, 60, 68, 0.7))
    p.setBrush(hsla(hue, 18, 20, 0.75))
    p.drawEllipse(g)
    p.setPen(QColor("#e8ecf0"))
    p.setFont(QFont("Noto Sans", 18))
    p.drawText(g, Qt.AlignmentFlag.AlignCenter, "⚙")
    # the laser, holding the right strip
    p.setPen(QPen(hsla(hue, 70, 75, 0.8), 3))
    p.drawLine(right.center().x(), right.y() + 330, w - 20, h - 10)
    p.end()
    img.save(str(OUT / "scroll-strips.png"))
    print(f"docs/images/scroll-strips.png  {w}x{h}")


VIEWS = {"arrowpad": arrowpad, "arrowpad-tools": lambda: arrowpad(tools=True), "snip": snip,
         "narrate": narrate, "wallet": wallet, "memory-limits": memory, "scroll-strips": scroll_strips,
         "menu-icons": menu_icons, "recline": recline}

if __name__ == "__main__":
    names = sys.argv[1:] or list(VIEWS)
    bad = [n for n in names if n not in VIEWS]
    if bad:
        sys.exit(f"unknown: {' '.join(bad)} (one of: {' '.join(VIEWS)})")
    OUT.mkdir(parents=True, exist_ok=True)
    for n in names:
        VIEWS[n]()
