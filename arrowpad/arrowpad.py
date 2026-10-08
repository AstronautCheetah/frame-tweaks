#!/usr/bin/env python3
"""Arrow Pad: a small always-on-top key pad for SteamOS desktop mode, with the
keys the Steam on-screen keyboard lacks: arrows, Home/End, PgUp/PgDn, Esc,
Ctrl/Alt/Super, F1-F12, clipboard shortcuts and a dictation button.

How it works
  * The window runs under XWayland with the "does not accept focus" hint, so
    tapping a button never steals keyboard focus from the app you're typing in.
  * Keys are injected as real key down/up events through ydotoold's socket
    (kernel uinput), so they reach any app. Holding a button holds the key, so
    the app's normal key repeat applies.
  * Modifiers: tap = one-shot (applies to the next key), double-tap = locked
    (until tapped again). A held modifier also applies to mouse clicks.
  * Launching it again toggles the running pad (hide/show) instead of opening
    a second one, so a keyboard shortcut or controller button can summon it.
"""
import argparse
import json
import os
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

# Must be set before Qt is imported: KWin only honours "no focus" for X11 windows.
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")


def pick_display(argv):
    """--desktop / --vr choose where the pad opens, whichever menu launched it.
    Desktop mode is a nested Plasma session with its own X display (:2 here) and
    X authority file; VR floating windows live on the Steam session's display :0."""
    if "--desktop" in argv:
        src = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "ksmserver"],
                             capture_output=True, text=True).stdout.split()
        if not src:
            sys.exit("arrowpad: desktop mode isn't running")
        env = dict(kv.split("=", 1) for kv in Path(f"/proc/{src[0]}/environ").read_text().split("\0") if "=" in kv)
        for k in ("DISPLAY", "XAUTHORITY"):
            if k in env:
                os.environ[k] = env[k]
        return "desktop"
    if "--vr" in argv:
        os.environ["DISPLAY"] = ":0"
        os.environ.pop("XAUTHORITY", None)
        return "vr"
    return "vr" if os.environ.get("DISPLAY") == ":0" else "desktop"


TARGET = pick_display(sys.argv)
if TARGET == "vr":
    # VR mode is a native SteamVR overlay (vroverlay.py), drawn off-screen: a floating window
    # would take keyboard focus when clicked, so its keys would go to itself.
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

from PyQt6.QtCore import QEvent, QObject, QPoint, QRectF, QSize, Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath  # noqa: E402
from PyQt6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLayout, QPushButton,  # noqa: E402
                             QVBoxLayout, QWidget)

try:  # controller haptics (optional): SteamVR Input via the openvr module
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from haptics import Haptics  # noqa: E402
except Exception:  # pragma: no cover
    Haptics = None

# Linux input-event-codes.h
EV_SYN, EV_KEY, SYN_REPORT = 0x00, 0x01, 0
KEY = {
    "Esc": 1, "Tab": 15, "Bksp": 14, "Del": 111, "Enter": 28, "Ins": 110,
    "Home": 102, "End": 107, "PgUp": 104, "PgDn": 109,
    "↑": 103, "↓": 108, "←": 105, "→": 106,
    "Shift": 42, "Ctrl": 29, "Alt": 56, "Super": 125,
    "PrtSc": 99, "Menu": 127,
    **{f"F{n}": c for n, c in zip(range(1, 11), range(59, 69))}, "F11": 87, "F12": 88,
    "A": 30, "C": 46, "V": 47, "X": 45, "Z": 44,
}
MODIFIERS = ("Shift", "Ctrl", "Alt", "Super")
CHORDS = {"Copy": "C", "Paste": "V", "Cut": "X", "Undo": "Z", "All": "A"}  # Ctrl + key
LAYERS = {
    "nav": [
        ["Esc", "Tab", "Bksp", "Del", "Enter", "Fn"],
        ["Shift", "Home", "↑", "End", "PgUp", "🎤"],
        ["Ctrl", "←", "↓", "→", "PgDn", "Copy"],
        ["Alt", "Super", "Undo", "Cut", "All", "Paste"],
    ],
    "fn": [
        ["F1", "F2", "F3", "F4", "F5", "Fn"],
        ["F6", "F7", "F8", "F9", "F10", "🎤"],
        ["F11", "F12", "Ins", "PrtSc", "Menu", "Copy"],
        ["Alt", "Super", "Undo", "Cut", "All", "Paste"],
    ],
}
# Key legends as printed on physical keyboards of each language (others keep English).
LABELS = {
    "en": {"Bksp": "Bksp", "PgUp": "PgUp", "PgDn": "PgDn", "PrtSc": "PrtSc"},
    "de": {"Bksp": "Rück", "Del": "Entf", "Ins": "Einfg", "Home": "Pos1", "End": "Ende",
           "PgUp": "Bild↑", "PgDn": "Bild↓", "PrtSc": "Druck", "Menu": "Menü", "Shift": "Umsch",
           "Ctrl": "Strg"},
    "fr": {"Esc": "Échap", "Bksp": "Retour", "Del": "Suppr", "Enter": "Entrée", "Ins": "Inser",
           "Home": "Début", "End": "Fin", "PgUp": "Pg↑", "PgDn": "Pg↓", "PrtSc": "Impr", "Shift": "Maj"},
    "es": {"Bksp": "Retro", "Del": "Supr", "Enter": "Intro", "Home": "Inicio", "End": "Fin",
           "PgUp": "RePág", "PgDn": "AvPág", "PrtSc": "ImpPt", "Menu": "Menú", "Shift": "Mayús"},
    "it": {"Del": "Canc", "Enter": "Invio", "Home": "Inizio", "End": "Fine", "PgUp": "Pag↑",
           "PgDn": "Pag↓", "PrtSc": "Stamp", "Shift": "Maiusc"},
}
LAYOUT_LANG = {"de": "de", "at": "de", "ch": "de", "fr": "fr", "be": "fr", "ca": "fr",
               "es": "es", "latam": "es", "it": "it"}
# Clipboard keys show icons (language-neutral), like Full Keyboard's copy/paste buttons.
BREEZE = Path("/usr/share/icons/breeze-dark")
ICONS = {"Copy": "edit-copy", "Paste": "edit-paste", "Cut": "edit-cut", "Undo": "edit-undo",
         "All": "edit-select-all", "pin": "window-pin", "reset": "crosshairs",
         "smaller": "zoom-out", "larger": "zoom-in", "close": "window-close"}
TIPS = {"🎤": "Dictation: tap to start (red), tap again to stop; yellow = transcribing, then it types",
        "Copy": "Copy (Ctrl+C)", "Paste": "Paste (Ctrl+V)", "Cut": "Cut (Ctrl+X)",
        "All": "Select all (Ctrl+A)", "Undo": "Undo (Ctrl+Z)", "Fn": "F1–F12 layer",
        **{m: f"{m}: tap = next key only, double-tap = lock" for m in MODIFIERS}}
DOUBLE_TAP = 0.4
SCALE_MIN, SCALE_MAX, SCALE_STEP = 0.6, 2.0, 0.1
RUN = Path(f"/run/user/{os.getuid()}")
CONFIG = Path.home() / f".config/arrowpad{'-vr' if TARGET == 'vr' else ''}.json"
SERVER_NAME = f"arrowpad-{os.getuid()}-{TARGET}"   # desktop and VR pads are separate instances
ICON = Path.home() / ".local/share/icons/hicolor/256x256/apps/frame-tweaks-arrowpad.png"

# Full Keyboard's "Graphite" theme (TaiKeid/steam-frame-full-keyboard, MIT).
THEME = {"surface": "#0b1016", "surface_radius": 20, "key_top": "#2c333b", "key_middle": "#232a32",
         "key_bottom": "#1c232a", "key_side": "#0c1015", "legend": "#ffffff", "key_radius": 8,
         "key_depth": 3.5, "hover": "#3d4855", "latched": "#355b7a"}


def stylesheet(scale):
    t = THEME
    r, d = round(t["key_radius"] * scale), max(2, round(t["key_depth"] * scale))
    grad = (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {t['key_top']}, "
            f"stop:0.5 {t['key_middle']}, stop:1 {t['key_bottom']})")
    return f"""
QPushButton {{ color: {t['legend']}; background: {grad}; border: none; border-radius: {r}px;
               border-bottom: {d}px solid {t['key_side']}; padding: 0; }}
QPushButton:hover {{ background: {t['hover']}; }}
QPushButton:pressed {{ background: {t['key_bottom']}; border-bottom-width: 1px; margin-top: {d - 1}px; }}
QPushButton[state="oneshot"] {{ background: {t['latched']}; }}
QPushButton[state="locked"]  {{ background: {t['latched']}; border: 2px solid #8fb8dd;
                                border-bottom: {d}px solid #8fb8dd; }}
QPushButton[state="active"]  {{ background: #c0392b; }}
QPushButton[state="busy"]    {{ background: #d9a400; color: black; }}
QPushButton[tool="true"] {{ background: {t['key_bottom']}; border-bottom: none; }}
QPushButton[tool="true"]:hover {{ background: {t['hover']}; }}
QPushButton[tool="true"][state="locked"] {{ background: {t['latched']}; border: none; }}
"""


def kde_layout():
    """Current KDE keyboard layout code (e.g. 'us', 'de'), from the desktop session."""
    env = dict(os.environ)
    src = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "ksmserver"],
                         capture_output=True, text=True).stdout.split()
    if src:   # the desktop's private D-Bus also works for the VR window
        try:
            senv = dict(kv.split("=", 1) for kv in Path(f"/proc/{src[0]}/environ").read_text().split("\0") if "=" in kv)
            env["DBUS_SESSION_BUS_ADDRESS"] = senv.get("DBUS_SESSION_BUS_ADDRESS", env.get("DBUS_SESSION_BUS_ADDRESS", ""))
        except OSError:
            pass
    try:
        q = ["qdbus6", "org.kde.keyboard", "/Layouts", "org.kde.KeyboardLayouts."]
        idx = int(subprocess.run(q[:3] + [q[3] + "getLayout"], env=env, capture_output=True,
                                 text=True, timeout=2).stdout.strip())
        out = subprocess.run(["qdbus6", "--literal"] + q[:3] + [q[3] + "getLayoutsList"], env=env,
                             capture_output=True, text=True, timeout=2).stdout
        codes = [c for c in __import__("re").findall(r'\(sss\) "([^"]*)"', out)]
        if codes:
            return codes[min(idx, len(codes) - 1)]
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    try:
        for line in (Path.home() / ".config/kxkbrc").read_text().splitlines():
            if line.startswith("LayoutList="):
                return line.split("=", 1)[1].split(",")[0].strip()
    except OSError:
        pass
    return os.environ.get("LANG", "en")[:2]


class Ydotool:
    """Minimal client for ydotoold: it accepts raw `struct input_event`
    datagrams on its unix socket and replays them on a uinput device."""

    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.connect(path)

    def _emit(self, type_, code, value):
        t = time.time()
        self.sock.send(struct.pack("llHHi", int(t), int((t % 1) * 1_000_000), type_, code, value))

    def key(self, code, down):
        self._emit(EV_KEY, code, 1 if down else 0)
        self._emit(EV_SYN, SYN_REPORT, 0)

    def tap(self, *codes):
        for c in codes:
            self.key(c, True)
        for c in reversed(codes):
            self.key(c, False)


def breeze_icon(name):
    hits = sorted(BREEZE.glob(f"*/*/{name}.svg"))
    return QIcon(str(hits[-1])) if hits else None


class ArrowPad(QWidget):
    def __init__(self, yd, scale):
        super().__init__(None, Qt.WindowType.Tool
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Arrow Pad" + (" (VR)" if TARGET == "vr" else ""))
        self.yd = yd
        self.mod_state = {m: "off" for m in MODIFIERS}   # off | oneshot | locked
        self.mod_tapped = {m: 0.0 for m in MODIFIERS}
        self.layer = "nav"
        self.lang = "en"
        self.drag_offset = None
        cfg = self.load_config()
        self.cfg = cfg
        self.overlay = None
        self.scale = cfg.get("scale", 1.5 if TARGET == "vr" else scale)   # VR: texture sharpness
        self.pinned = cfg.get("pinned", False)

        outer = QVBoxLayout(self)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)   # window = content size
        self.outer = outer
        self.haptics = None
        self.hover_filter = HoverHaptics(self)
        # toolbar: pin, reset position, smaller, larger ......... close
        bar = QHBoxLayout()
        self.tools = {}
        for name, tip in (("pin", "Pin: stop accidental moves"), ("reset", "Reset position"),
                          ("smaller", "Smaller"), ("larger", "Larger")):
            self.tools[name] = self.tool_button(name, tip)
            bar.addWidget(self.tools[name])
        bar.addStretch(1)
        self.tools["close"] = self.tool_button("close", "Close")
        bar.addWidget(self.tools["close"])
        outer.addLayout(bar)
        self.tools["pin"].clicked.connect(self.toggle_pin)
        self.tools["reset"].clicked.connect(self.reset_position)
        self.tools["smaller"].clicked.connect(lambda: self.resize_step(-1))
        self.tools["larger"].clicked.connect(lambda: self.resize_step(+1))
        self.tools["close"].clicked.connect(self.close)

        grid = QGridLayout()
        self.grid = grid
        self.buttons = []
        for r, row in enumerate(LAYERS["nav"]):
            for c, _ in enumerate(row):
                b = QPushButton()
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.pressed.connect(lambda r=r, c=c: self.on_press(r, c))
                b.released.connect(lambda r=r, c=c: self.on_release(r, c))
                b.installEventFilter(self.hover_filter)
                grid.addWidget(b, r, c)
                self.buttons.append((r, c, b))
        outer.addLayout(grid)

        self.apply_scale()
        self.update_language()
        QTimer(self, interval=500, timeout=self.refresh_mic).start()
        QTimer(self, interval=15000, timeout=self.update_language).start()   # layouts rarely change
        if TARGET == "vr":
            from vroverlay import OverlayHost
            self.overlay = OverlayHost(self, cfg)
            if Haptics:
                self.haptics = Haptics(already_initialised=True)
        else:
            if Haptics:
                self.haptics = Haptics()
            if cfg.get("pos"):
                self.move(QPoint(*cfg["pos"]))
            else:
                QTimer.singleShot(0, self.reset_position)

    def tool_button(self, name, tip):
        b = QPushButton()
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setProperty("tool", "true")
        b.setToolTip(tip)
        icon = breeze_icon(ICONS[name])
        if icon:
            b.setIcon(icon)
        else:
            b.setText({"pin": "📌", "reset": "⌖", "smaller": "−", "larger": "+", "close": "✕"}[name])
        return b

    # ---- looks ----------------------------------------------------------
    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        r = THEME["surface_radius"] * self.scale
        path.addRoundedRect(QRectF(self.rect()), r, r)
        p.fillPath(path, QColor(THEME["surface"]))

    def apply_scale(self):
        s = self.scale
        key, gap, pad, tool = round(52 * s), round(6 * s), round(12 * s), round(34 * s)
        self.setStyleSheet(stylesheet(s))
        self.outer.setContentsMargins(pad, pad, pad, pad)
        self.outer.setSpacing(round(10 * s))
        self.grid.setSpacing(gap)
        for b in self.tools.values():
            b.setFixedSize(round(tool * 1.4), tool)
            b.setIconSize(QSize(round(tool * 0.6), round(tool * 0.6)))
        for _, _, b in self.buttons:
            b.setFixedSize(key, key)
            b.setIconSize(QSize(round(key * 0.45), round(key * 0.45)))
        self.relabel()
        self.adjustSize()

    def resize_step(self, steps):
        """+/-: in VR the overlay's width (5 cm steps, like Full Keyboard); else key size."""
        if self.overlay:
            self.overlay.step_width(steps)
        else:
            self.set_scale(self.scale + steps * SCALE_STEP)

    def set_scale(self, value):
        self.scale = round(min(SCALE_MAX, max(SCALE_MIN, value)), 2)
        self.apply_scale()
        self.save_config()

    def label(self, name):
        return LABELS.get(self.lang, {}).get(name, LABELS["en"].get(name, name))

    def relabel(self):
        key = round(52 * self.scale)
        for r, c, b in self.buttons:
            name = self.name_at(r, c)
            b.setToolTip(TIPS.get(name, ""))
            icon = breeze_icon(ICONS[name]) if name in CHORDS else None
            if icon:
                b.setIcon(icon)
                b.setText("")
                continue
            b.setIcon(QIcon())
            text = self.label(name)
            b.setText(text)
            # Fit the legend: big for single glyphs, shrink long words to the key width.
            f = QFont(QApplication.font())
            size = round(key * (0.42 if len(text) <= 1 else 0.26))
            f.setPixelSize(size)
            if name == "🎤":    # colour emoji, matching the Dictate menu icon
                f.setFamilies(["Noto Color Emoji", f.family()])
            while size > 8 and QFontMetrics(f).horizontalAdvance(text) > key - round(8 * self.scale):
                size -= 1
                f.setPixelSize(size)
            b.setFont(f)
        self.restyle()

    def update_language(self):
        lang = LAYOUT_LANG.get(kde_layout().split("(")[0].lower(), "en")
        if lang != self.lang:
            self.lang = lang
            self.relabel()

    def name_at(self, r, c):
        return LAYERS[self.layer][r][c]

    def restyle(self):
        for r, c, b in self.buttons:
            name = self.name_at(r, c)
            if name in MODIFIERS:
                state = self.mod_state[name]
            elif name == "Fn":
                state = "locked" if self.layer == "fn" else "off"
            elif name == "🎤":
                state = {"recording": "active", "transcribing": "busy"}.get(self.dictation_state(), "off")
            else:
                state = "off"
            self.set_state(b, state)
        self.set_state(self.tools["pin"], "locked" if self.pinned else "off")

    @staticmethod
    def set_state(b, state):
        if b.property("state") != state:
            b.setProperty("state", state)
            b.style().unpolish(b)
            b.style().polish(b)

    # ---- grab to move, pin, reset ----------------------------------------
    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and not self.pinned:
            self.drag_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev):
        if self.drag_offset is not None:
            self.move(ev.globalPosition().toPoint() - self.drag_offset)

    def mouseReleaseEvent(self, ev):
        if self.drag_offset is not None:
            self.drag_offset = None
            self.save_config()

    def toggle_pin(self):
        self.pinned = not self.pinned
        self.restyle()
        self.save_config()

    def reset_position(self):
        """Bottom centre of the screen, like Full Keyboard's recenter (size is kept)."""
        if self.overlay:
            self.overlay.reset_position()
            return
        screen = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        self.adjustSize()
        self.move(screen.x() + (screen.width() - self.width()) // 2,
                  screen.y() + screen.height() - self.height() - round(24 * self.scale))
        self.save_config()

    # ---- input ----------------------------------------------------------
    def pulse(self, kind, device=None):
        if device is None and self.overlay is not None:
            device = self.overlay.last_device      # the controller that just pressed
        if self.haptics:
            self.haptics.pulse(kind, device)

    def on_press(self, r, c):
        self.pulse("press")
        name = self.name_at(r, c)
        if name in KEY and name not in MODIFIERS:
            self.yd.key(KEY[name], True)

    def on_release(self, r, c):
        name = self.name_at(r, c)
        if name in MODIFIERS:
            self.toggle_mod(name)
        elif name == "Fn":
            self.layer = "fn" if self.layer == "nav" else "nav"
            self.relabel()
        elif name == "🎤":
            subprocess.Popen([str(Path.home() / ".local/bin/dictate")], start_new_session=True)
            QTimer.singleShot(300, self.restyle)
        elif name in CHORDS:
            ctrl_held = self.mod_state["Ctrl"] != "off"
            codes = ([] if ctrl_held else [KEY["Ctrl"]]) + [KEY[CHORDS[name]]]
            self.yd.tap(*codes)
            self.release_oneshots()
        elif name in KEY:
            self.yd.key(KEY[name], False)
            self.release_oneshots()

    def toggle_mod(self, name):
        now, state = time.monotonic(), self.mod_state[name]
        if state == "off":
            self.mod_state[name] = "oneshot"
            self.yd.key(KEY[name], True)
        elif state == "oneshot" and now - self.mod_tapped[name] < DOUBLE_TAP:
            self.mod_state[name] = "locked"
        else:
            self.mod_state[name] = "off"
            self.yd.key(KEY[name], False)
        self.mod_tapped[name] = now
        self.restyle()

    def release_oneshots(self):
        for m, s in self.mod_state.items():
            if s == "oneshot":
                self.mod_state[m] = "off"
                self.yd.key(KEY[m], False)
        self.restyle()

    def release_all_mods(self):
        for m, s in self.mod_state.items():
            if s != "off":
                self.yd.key(KEY[m], False)
                self.mod_state[m] = "off"

    # ---- dictation ------------------------------------------------------
    @staticmethod
    def dictation_state():
        """recording / transcribing / idle, from dictate's pid files."""
        for name, state in (("rec.pid", "recording"), ("busy.pid", "transcribing")):
            try:
                os.kill(int((RUN / "dictate" / name).read_text()), 0)
                return state
            except (OSError, ValueError):
                pass
        return "idle"

    def refresh_mic(self):
        if self.isVisible():
            self.restyle()

    # ---- window / settings ----------------------------------------------
    def toggle_visible(self):
        if self.overlay:          # VR: relaunching recenters it in front of you (Full Keyboard does too)
            self.overlay.reset_position()
            return
        if self.isVisible():
            self.save_config()
            self.release_all_mods()
            self.hide()
        else:
            self.show()
            self.raise_()

    @staticmethod
    def load_config():
        try:
            return json.loads(CONFIG.read_text())
        except (OSError, ValueError):
            return {}

    def save_config(self):
        try:
            self.cfg.update({"pos": [self.x(), self.y()], "scale": self.scale, "pinned": self.pinned})
            CONFIG.write_text(json.dumps(self.cfg))
        except OSError:
            pass

    def closeEvent(self, ev):
        self.save_config()
        self.release_all_mods()   # never leave a modifier stuck down
        if self.overlay:
            self.overlay.close()
        if self.haptics:
            self.haptics.close()
        super().closeEvent(ev)
        QApplication.quit()


class HoverHaptics(QObject):
    """A light tick when the pointer moves onto a key (not the toolbar), like Full Keyboard."""

    def __init__(self, pad):
        super().__init__(pad)
        self.pad = pad

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Enter and self.pad.overlay is None:
            self.pad.pulse("hover")
        return False


def default_socket():
    return os.environ.get("YDOTOOL_SOCKET") or str(RUN / ".ydotool_socket")


def signal_running(command):
    """Send a command to an already running pad; True if one answered."""
    s = QLocalSocket()
    s.connectToServer(SERVER_NAME)
    if not s.waitForConnected(300):
        return False
    s.write(command.encode())
    s.waitForBytesWritten(300)
    s.disconnectFromServer()
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scale", type=float, default=float(os.environ.get("ARROWPAD_SCALE", 1.0)),
                    help="button size multiplier (default 1.0)")
    ap.add_argument("--socket", default=default_socket(), help="ydotoold socket path")
    ap.add_argument("--quit", action="store_true", help="close a running pad")
    ap.add_argument("--desktop", action="store_true", help="open in desktop mode (even from the VR menu)")
    ap.add_argument("--vr", action="store_true", help="open as a floating VR window")
    args = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("arrowpad")
    # Taskbar/window icon instead of the generic X11 logo; the desktop file name lets
    # KWin match the window to its menu entry.
    app.setDesktopFileName("arrowpad-vr" if TARGET == "vr" else "arrowpad")
    if ICON.exists():
        app.setWindowIcon(QIcon(str(ICON)))
    if signal_running("quit" if args.quit else "toggle") or args.quit:
        return
    try:
        yd = Ydotool(args.socket)
    except OSError as e:
        sys.exit(f"arrowpad: cannot reach ydotoold at {args.socket}: {e}\n"
                 "Start it with: systemctl --user start ydotoold")

    pad = ArrowPad(yd, args.scale)
    QLocalServer.removeServer(SERVER_NAME)   # stale socket from a crashed instance
    server = QLocalServer()
    server.listen(SERVER_NAME)

    def on_client():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(300)
        cmd = bytes(conn.readAll()).decode()
        if cmd == "quit":
            pad.close()
            app.quit()
        else:
            pad.toggle_visible()
    server.newConnection.connect(on_client)

    pad.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
