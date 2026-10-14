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

sys.path.insert(0, str(Path.home() / ".local/share/frame-tweaks/i18n"))   # (lib/common.sh install_i18n)
try:
    import i18n
    from i18n import _, N_, NP_, ngettext, pgettext  # noqa: F401
except ImportError:                       # (not installed by Frame Tweaks: English)
    i18n = None

    def _(text):
        return text

    def ngettext(singular, plural, n):
        return singular if n == 1 else plural

    def pgettext(context, text):
        return text

    def NP_(context, text):
        return text
    N_ = _

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
            sys.exit(_("arrowpad: desktop mode isn't running"))
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
    "A": 30, "C": 46, "V": 47, "X": 45, "Z": 44, "F": 33, "S": 31,
}
MODIFIERS = ("Ctrl", "Alt", "Super")
MOUSE = ("RMB", "MMB")       # toggles: the next click becomes a right / middle click
CHORDS = {"Copy": "C", "Paste": "V", "Cut": "X", "Undo": "Z", "All": "A",   # Ctrl + key(s)
          "Redo": ("Shift", "Z"), "Find": "F", "Save": "S"}
LAYERS = {
    # Keys found on more than one layer keep their place on all of them (Tools, Esc, Fn, the
    # modifiers, R/M, and the clipboard keys); only the rest change.
    "nav": [
        ["Tools", "Tab", "Bksp", "Del", "RMB", "MMB"],
        ["Fn", "Home", "↑", "End", "PgUp", "Esc"],
        ["Ctrl", "←", "↓", "→", "PgDn", "Copy"],
        ["Alt", "Super", "Undo", "Cut", "All", "Paste"],
    ],
    "fn": [
        ["Tools", "F1", "F2", "F3", "RMB", "MMB"],
        ["Fn", "F4", "F5", "F6", "F7", "Esc"],
        ["Ctrl", "F8", "F9", "F10", "F11", "Copy"],
        ["Alt", "Super", "F12", "Ins", "PrtSc", "Paste"],
    ],
    # Tools: screen snip, dictation and more shortcuts, in the arrow and navigation keys' places.
    "tools": [
        ["Tools", "Tab", "Bksp", "Del", "RMB", "MMB"],
        ["Fn", "Snip", "🎤", "Launcher", "Save", "Esc"],
        ["Ctrl", "Find", "Redo", "Enter", "Unstick", "Copy"],
        ["Alt", "Super", "Undo", "Cut", "All", "Paste"],
    ],
}
# Key legends: translated like any text, in the context "key legend" (locale/glossary: what that
# language's keyboards print, else the ISO/IEC 9995-7 key symbol). Arrows, F-keys and the rest keep
# their legend.
LEGENDS = {"Esc": NP_("key legend", "Esc"), "Tab": NP_("key legend", "Tab"), "Bksp": NP_("key legend", "Bksp"),
           "Del": NP_("key legend", "Del"), "Enter": NP_("key legend", "Enter"), "Ins": NP_("key legend", "Ins"),
           "Home": NP_("key legend", "Home"), "End": NP_("key legend", "End"), "PgUp": NP_("key legend", "PgUp"),
           "PgDn": NP_("key legend", "PgDn"), "PrtSc": NP_("key legend", "PrtSc"), "Menu": NP_("key legend", "Menu"),
           "Shift": NP_("key legend", "Shift"), "Ctrl": NP_("key legend", "Ctrl"), "Alt": NP_("key legend", "Alt"),
           "Super": NP_("key legend", "Super")}
# The mouse keys show the first letter of the button's name (Right: R; in Spanish, Derecho: D).
MOUSE_WORDS = {"RMB": NP_("mouse button", "Right"), "MMB": NP_("mouse button", "Middle")}
# Legends for languages that have no translation yet (from their keyboards), until they do.
SEED_LEGENDS = {
    "de": {"Bksp": "Rück", "Del": "Entf", "Ins": "Einfg", "Home": "Pos1", "End": "Ende",
           "PgUp": "Bild↑", "PgDn": "Bild↓", "PrtSc": "Druck", "Menu": "Menü", "Shift": "Umsch",
           "Ctrl": "Strg"},
    "fr": {"Esc": "Échap", "Bksp": "Retour", "Del": "Suppr", "Enter": "Entrée", "Ins": "Inser",
           "Home": "Début", "End": "Fin", "PgUp": "Pg↑", "PgDn": "Pg↓", "PrtSc": "Impr", "Shift": "Maj"},
    "it": {"Del": "Canc", "Enter": "Invio", "Home": "Inizio", "End": "Fine", "PgUp": "Pag↑",
           "PgDn": "Pag↓", "PrtSc": "Stamp", "Shift": "Maiusc"},
}
# Clipboard keys show icons (language-neutral), like Full Keyboard's copy/paste buttons.
BREEZE = Path("/usr/share/icons/breeze-dark")
ICONS = {"Copy": "edit-copy", "Paste": "edit-paste", "Cut": "edit-cut", "Undo": "edit-undo",
         "All": "edit-select-all", "pin": "window-unpin", "pin_on": "window-pin", "reset": "crosshairs",
         "RMB": "input-mouse-click-right", "MMB": "input-mouse-click-middle",
         "smaller": "zoom-out", "larger": "zoom-in", "close": "window-close", "Snip": "select-rectangular",
         "Redo": "edit-redo", "Find": "edit-find", "Save": "document-save"}
# Tooltips: marked here, translated where shown ({m} is the modifier's key name).
TIPS = {"🎤": N_("Dictation: tap to start (red), tap again to stop; yellow = transcribing, then it types"),
        "Copy": N_("Copy (Ctrl+C)"), "Paste": N_("Paste (Ctrl+V)"), "Cut": N_("Cut (Ctrl+X)"),
        "All": N_("Select all (Ctrl+A)"), "Undo": N_("Undo (Ctrl+Z)"), "Fn": N_("F1–F12 layer (tap again to go back)"),
        "Redo": N_("Redo (Ctrl+Shift+Z)"), "Find": N_("Find (Ctrl+F)"), "Save": N_("Save (Ctrl+S)"),
        "Tools": N_("Tools layer: screen snip, dictation, editing shortcuts (tap again to go back)"),
        "Snip": N_("Screen snip: select a rectangle, then copy it, save it, copy its text or read it aloud"),
        "Unstick": N_("Unstick keys: the desktop acts as if Shift, Ctrl, Alt or Super were held? Tap this"),
        "RMB": N_("Right click: your next click becomes a right click"),
        "Launcher": N_("Open the desktop's application menu (taps Super)"),
        "Super": N_("Super (Meta): tap = next key only, double-tap = lock; hold it while pressing a key with the other hand"),
        "MMB": N_("Middle click: your next click becomes a middle click"),
        **{m: N_("{m}: tap = next key only, double-tap = lock; or hold it while pressing a key with the other hand")
           for m in MODIFIERS if m != "Super"}}
TOOL_TIPS = {"settings": N_("Settings: theme and haptics"), "pin": N_("Pin: stop accidental moves"),
             "reset": N_("Reset position"), "smaller": N_("Smaller"), "larger": N_("Larger"), "close": N_("Close"),
             "fold": N_("Collapse"), "unfold": N_("Expand")}
# Keys whose legend is a word rather than a key name (translated where shown).
# (context "key legend": a translation short enough for a key, e.g. "Herram." for Herramientas)
WORDS = {"Tools": NP_("key legend", "Tools"), "Unstick": NP_("key legend", "Unstick"),
         "Snip": NP_("key legend", "Snip"), "Launcher": NP_("key legend", "Launcher")}
DOUBLE_TAP = 0.4
SCALE_MIN, SCALE_MAX, SCALE_STEP = 0.6, 2.0, 0.1
RUN = Path(f"/run/user/{os.getuid()}")
CONFIG = Path.home() / f".config/arrowpad{'-vr' if TARGET == 'vr' else ''}.json"
SERVER_NAME = f"arrowpad-{os.getuid()}-{TARGET}"   # desktop and VR pads are separate instances
ICON = Path.home() / ".local/share/icons/hicolor/256x256/apps/frame-tweaks-arrowpad.png"

# Full Keyboard's two themes (TaiKeid/steam-frame-full-keyboard share/framekeyboard/themes, MIT).
THEMES = {
    "graphite": {"name": N_("Graphite"), "surface": "#0b1016", "surface_radius": 20, "key_top": "#2c333b",
                 "key_middle": "#232a32", "key_bottom": "#1c232a", "key_side_top": "#141a21",
                 "key_side_bottom": "#0c1015", "legend": "#ffffff", "key_radius": 8, "key_depth": 3.5,
                 "key_press_travel": 3, "press_duration_ms": 80, "hover": "#3d4855", "latched": "#355b7a"},
    "midnight": {"name": N_("Midnight"), "surface": "#20242c", "surface_radius": 20, "key_top": "#505d72",
                 "key_middle": "#455063", "key_bottom": "#374252", "key_side_top": "#293241",
                 "key_side_bottom": "#191f29", "legend": "#ffffff", "key_radius": 8, "key_depth": 3.5,
                 "key_press_travel": 3, "press_duration_ms": 80, "hover": "#687c99", "latched": "#387d8d"},
}
THEME = dict(THEMES["graphite"])        # the current theme; set_theme() switches it in place
HAPTIC_LEVELS = {"off": 0.0, "light": 0.5, "normal": 1.0}
HAPTIC_NAMES = {"off": N_("Off"), "light": N_("Light"), "normal": N_("Normal")}
SETTING_TITLES = {"Theme": N_("Theme"), "Haptics": N_("Haptics")}


def stylesheet(scale):
    t = THEME
    r, d = round(t["key_radius"] * scale), max(2, round(t["key_depth"] * scale))
    grad = (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {t['key_top']}, "
            f"stop:0.5 {t['key_middle']}, stop:1 {t['key_bottom']})")
    return f"""
QPushButton {{ color: {t['legend']}; background: {grad}; border: none; border-radius: {r}px;
               border-bottom: {d}px solid {t['key_side_bottom']}; padding: 0; }}
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
QLabel {{ color: {t['legend']}; }}
"""


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

    def clear_stuck_modifiers(self):
        """At start: make the desktop forget modifiers a previous pad may have left "held" (a
        crash can't send the release). Same sequence as lib/common.sh's clear_stuck_modifiers:
        full press+release each, Super and Alt around F24 so it isn't a lone tap (no menu opens)."""
        F24 = 194
        # Shift (both sides), left Ctrl. Never Right Ctrl: in the nested desktop it toggles KWin's
        # input grab ("Press right control to grab input"), which upsets windows and clicks.
        for code in (42, 54, 29):
            self.key(code, True)
            self.key(code, False)
        for code in (56, 125):                             # Alt, Super
            self.key(code, True)
            self.key(F24, True)
            self.key(F24, False)
            self.key(code, False)

    def tap(self, *codes):
        for c in codes:
            self.key(c, True)
        for c in reversed(codes):
            self.key(c, False)


class ClickSwap:
    """Right/middle-click toggles: the next click anywhere in the Steam session is replayed as
    the chosen button. Laser and mouse clicks don't pass through any input device we can read,
    so this grabs the pointer on the Steam session's X display (:0, which holds every floating
    window and the desktop) for one click, then replays it there with XTEST. One click, then
    it's released; also after TIMEOUT seconds, when toggled off, and (like Full Keyboard, which
    releases its input when the dashboard closes) when the pad is hidden. Scroll-wheel "buttons"
    pass straight through. Every step is logged to LOG for diagnosis."""
    TIMEOUT = 10
    RELEASE_WAIT = 1.5            # a press whose release never reaches us is replayed anyway
    LOG = RUN / "arrowpad-clicks.log"
    BUTTONS = {"RMB": 3, "MMB": 2}

    def __init__(self, on_done):
        import ctypes as C
        self.C, self.on_done = C, on_done
        self.x = self.t = self.dpy = None
        self.armed = None                 # "RMB" / "MMB" while waiting for the click
        self.press = None
        self.timer = QTimer(interval=15, timeout=self.poll)
        self.deadline = 0.0
        self.press_time = 0.0

    def log(self, msg):
        try:
            if self.LOG.exists() and self.LOG.stat().st_size > 200_000:
                self.LOG.replace(self.LOG.with_suffix(".log.1"))
            with open(self.LOG, "a") as f:
                f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
        except OSError:
            pass

    def _open(self):
        if self.dpy:
            return True
        C = self.C
        try:
            x, t = C.CDLL("libX11.so.6"), C.CDLL("libXtst.so.6")
        except OSError:
            return False
        x.XOpenDisplay.restype = C.c_void_p
        x.XDefaultRootWindow.restype = C.c_ulong
        x.XDefaultRootWindow.argtypes = [C.c_void_p]
        x.XGrabPointer.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_uint, C.c_int, C.c_int,
                                   C.c_ulong, C.c_ulong, C.c_ulong]
        x.XUngrabPointer.argtypes = [C.c_void_p, C.c_ulong]
        x.XPending.argtypes = [C.c_void_p]
        x.XNextEvent.argtypes = [C.c_void_p, C.c_void_p]
        x.XFlush.argtypes = [C.c_void_p]
        t.XTestFakeMotionEvent.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_ulong]
        t.XTestFakeButtonEvent.argtypes = [C.c_void_p, C.c_uint, C.c_int, C.c_ulong]
        display = os.environ.get("ARROWPAD_CLICK_DISPLAY") or (      # override: tests only
            ":0" if Path("/tmp/.X11-unix/X0").exists() else os.environ.get("DISPLAY", ""))
        self.dpy = x.XOpenDisplay(display.encode())
        self.x, self.t = x, t
        return bool(self.dpy)

    def arm(self, which):
        """Toggle `which` ("RMB"/"MMB"); arming one disarms the other. Returns the armed one."""
        if self.armed == which:
            self.disarm("toggled off")
            return None
        self.disarm(f"switched to {which}")
        if not self._open():
            return None
        r = self.grab()
        if r != 0:
            self.log(f"{which}: couldn't grab the pointer (result {r}); nothing changed")
            return None
        self.log(f"{which}: armed, waiting up to {self.TIMEOUT} s for a click")
        self.armed, self.press = which, None
        self.deadline = time.monotonic() + self.TIMEOUT
        self.timer.start()
        return which

    def grab(self):
        root = self.x.XDefaultRootWindow(self.dpy)
        # owner_events False, ButtonPress|ButtonRelease, async pointer and keyboard
        r = self.x.XGrabPointer(self.dpy, root, 0, (1 << 2) | (1 << 3), 1, 1, 0, 0, 0)
        self.x.XFlush(self.dpy)
        return r

    def ungrab(self):
        self.x.XUngrabPointer(self.dpy, 0)
        self.x.XFlush(self.dpy)

    def disarm(self, why=None):
        if self.armed and self.dpy:
            self.ungrab()
            if why:
                self.log(f"{self.armed}: cancelled ({why})")
        self.armed, self.press = None, None
        self.timer.stop()

    def replay(self, button, x=None, y=None):
        """Send a press+release of `button` (at x, y) to whatever is under the pointer."""
        if x is not None:
            self.t.XTestFakeMotionEvent(self.dpy, -1, x, y, 0)
        self.t.XTestFakeButtonEvent(self.dpy, button, 1, 0)
        self.t.XTestFakeButtonEvent(self.dpy, button, 0, 0)
        self.x.XFlush(self.dpy)

    def poll(self):
        try:
            self._poll()
        except Exception:
            self.disarm()             # never leave the pointer grabbed
            self.on_done()

    def _poll(self):
        now = time.monotonic()
        if self.press is not None and now - self.press_time > self.RELEASE_WAIT:
            self.finish("release never arrived")
            return
        if now > self.deadline:
            self.disarm(f"no click within {self.TIMEOUT} s")
            self.on_done()
            return
        ev = (self.C.c_long * 24)()
        while self.armed and self.x.XPending(self.dpy):
            self.x.XNextEvent(self.dpy, ev)
            ints = self.C.cast(ev, self.C.POINTER(self.C.c_int))
            etype = ints[0]
            # XButtonEvent: type, serial, send_event, display, window, root, subwindow, time,
            # x, y, x_root, y_root, state, button (64-bit: longs/pointers are 8 bytes)
            base = 8 * 8 // 4                                 # int index after the 8 long-sized fields
            x_root, y_root, button = ints[base + 2], ints[base + 3], ints[base + 5]
            if button >= 4:
                # Scroll wheel (4-7): not a click. Let it through: ungrab, replay, grab again.
                if etype == 4:
                    self.ungrab()
                    self.replay(button)
                    if self.grab() != 0:
                        self.disarm("couldn't grab again after a scroll")
                        self.on_done()
                        return
                continue
            if etype == 4:                                     # ButtonPress
                self.press, self.press_time = (x_root, y_root, button), time.monotonic()
            elif etype == 5 and self.press is not None:        # ButtonRelease: replay as chosen
                self.finish()
                return

    def finish(self, note=""):
        px, py, orig = self.press
        which = self.armed
        self.disarm()
        self.replay(self.BUTTONS[which], px, py)
        self.log(f"{which}: button {orig} at {px},{py} replayed as button {self.BUTTONS[which]}"
                 + (f" ({note})" if note else ""))
        self.on_done()


def drawn_icon(name, px=96, color=THEME["legend"]):
    """Full Keyboard's vector icons, redrawn with QPainter: same 24-unit coordinates, 1.8-unit
    round strokes, so the toolbar and clipboard keys match it exactly. None for names it doesn't
    draw. Ported from TaiKeid/steam-frame-full-keyboard src/panel.cpp under the MIT License:
    Copyright (c) 2026 TaiKeid and contributors. Permission is hereby granted, free of charge,
    to any person obtaining a copy of this software and associated documentation files, to deal
    in the Software without restriction, subject to including this copyright and permission
    notice in all copies or substantial portions. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT
    WARRANTY OF ANY KIND (full text: https://github.com/TaiKeid/steam-frame-full-keyboard/blob/main/LICENSE)."""
    from PyQt6.QtGui import QPen, QPixmap
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(px / 2, px / 2)
    p.scale(px / 24, px / 24)
    p.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    path = QPainterPath()

    def line(x1, y1, x2, y2):
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)

    def pin(off):
        nonlocal path
        if off:
            p.rotate(0.65 * 180 / 3.141592653589793)
        line(-5, -9, 5, -9)
        line(-4, -9, -4, -1)
        line(4, -9, 4, -1)
        path.moveTo(-4, -1)
        path.lineTo(-8, 3)
        path.lineTo(8, 3)
        path.lineTo(4, -1)
        line(0, 3, 0, 10)
        if off:
            p.drawPath(path)
            p.rotate(-0.65 * 180 / 3.141592653589793)
            path = QPainterPath()
            line(-10, -10, 10, 10)

    if name in ("Super", "Launcher"):               # filled logos: SteamFrame / SteamOS
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        if name == "Super":                         # traced from a 194-unit mark, as in Full Keyboard
            p.scale(24 / 194, 24 / 194)
            p.translate(-225.5, -225.5)
            path.moveTo(131.5, 128.5); path.lineTo(319.5, 128.5); path.lineTo(322.5, 131.5)
            path.lineTo(322.5, 176); path.lineTo(176, 176); path.lineTo(176, 322.5)
            path.lineTo(131.5, 322.5); path.lineTo(128.5, 319.5); path.lineTo(128.5, 131.5)
            path.closeSubpath()
            path.moveTo(322.5, 322.5)
            path.arcTo(QRectF(322.5 - 128, 322.5 - 128, 256, 256), 180, -90)
            path.closeSubpath()
        else:                                       # concentric dot and half ring
            path.addEllipse(QRectF(-9, -6, 12, 12))
            path.moveTo(-3, -12)
            path.arcTo(QRectF(-15, -12, 24, 24), 90, -180)
            path.lineTo(-3, 7.8)
            path.arcTo(QRectF(-10.8, -7.8, 15.6, 15.6), 270, 180)
            path.closeSubpath()
        p.drawPath(path)
        p.end()
        return QIcon(pm)
    if name == "settings":                          # gear: 32 points, flat-tipped teeth
        import math as _m
        for i in range(32):
            a = i * _m.pi / 16
            rad = 11 if i % 4 < 2 else 8.5
            (path.moveTo if i == 0 else path.lineTo)(rad * _m.cos(a), rad * _m.sin(a))
        path.closeSubpath()
        path.addEllipse(QRectF(-3.5, -3.5, 7, 7))
    elif name in ("pin_on", "pin"):
        pin(name == "pin")                                   # "pin" = not pinned: tilted, crossed out
    elif name == "reset":                                     # Recenter
        path.addEllipse(QRectF(-7, -7, 14, 14))
        line(-11, 0, -5, 0); line(5, 0, 11, 0); line(0, -11, 0, -5); line(0, 5, 0, 11)
    elif name in ("smaller", "larger"):                       # ScaleDown / ScaleUp
        path.addEllipse(QRectF(-11, -11, 16, 16))
        line(3, 3, 10, 10); line(-7, -3, 1, -3)
        if name == "larger":
            line(-3, -7, -3, 1)
    elif name == "close":
        line(-7, -7, 7, 7); line(7, -7, -7, 7)
    elif name == "fold":                                      # (ours) Collapse: a down chevron, as Screen snip's
        line(-8, -3, 0, 5); line(0, 5, 8, -3)
    elif name == "unfold":                                    # (ours) Expand: an up chevron
        line(-8, 3, 0, -5); line(0, -5, 8, 3)
    elif name == "Copy":
        path.addRoundedRect(QRectF(-3, -3, 13, 14), 2, 2)
        path.moveTo(4, -6); path.lineTo(4, -9); path.lineTo(-10, -9); path.lineTo(-10, 5); path.lineTo(-6, 5)
    elif name == "Paste":
        path.moveTo(-5, -8); path.lineTo(-9, -8); path.lineTo(-9, 11); path.lineTo(9, 11)
        path.lineTo(9, -8); path.lineTo(5, -8)
        path.addRoundedRect(QRectF(-5, -11, 10, 6), 2, 2)
        line(-4, 0, 4, 0); line(-4, 5, 2, 5)
    else:
        p.end()
        return None
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def icon_for(name):
    """Full Keyboard's drawn icon where it has one, else Breeze's."""
    return drawn_icon(name) or (breeze_icon(ICONS[name]) if name in ICONS else None)


class KeyButton(QPushButton):
    """A key drawn the way Full Keyboard draws one: a darker side, and a fixed-size face that
    travels down by key_press_travel when pressed (over press_duration_ms), with a hover
    gradient. State (property "state"): off, oneshot/held/locked (latched), active, busy."""

    def __init__(self, pad):
        super().__init__()
        self.pad = pad
        self._amount = 0.0
        from PyQt6.QtCore import QVariantAnimation
        self.anim = QVariantAnimation(self)
        self.anim.valueChanged.connect(self._set_amount)
        self.pressed.connect(lambda: self._animate(1.0))
        self.released.connect(lambda: self._animate(0.0))

    def _set_amount(self, v):
        self._amount = float(v)
        self.update()

    def _animate(self, target):
        self.anim.stop()
        self.anim.setDuration(int(THEME["press_duration_ms"]))
        self.anim.setStartValue(self._amount)
        self.anim.setEndValue(target)
        self.anim.start()

    def paintEvent(self, ev):
        from PyQt6.QtGui import QLinearGradient, QPen
        t, sc = THEME, self.pad.scale
        w, h = self.width(), self.height()
        depth, travel, r = t["key_depth"] * sc, t["key_press_travel"] * sc, t["key_radius"] * sc
        face_h = h - depth
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        def grad(rect, a, b, c=None):
            g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            g.setColorAt(0, QColor(a))
            if c is None:
                g.setColorAt(1, QColor(b))
            else:
                g.setColorAt(.5, QColor(b))
                g.setColorAt(1, QColor(c))
            return g
        side = QRectF(0, travel, w, face_h + depth - travel)
        p.setBrush(grad(side, t["key_side_top"], t["key_side_bottom"]))
        p.drawRoundedRect(side, r, r)
        # In VR the image is a snapshot, so a held key shows fully down even between frames.
        amount = 1.0 if self.isDown() else self._amount
        face = QRectF(0, amount * travel, w, face_h)
        state = self.property("state") or "off"
        fills = {"active": "#c0392b", "busy": "#d9a400"}
        if state in fills:
            p.setBrush(QColor(fills[state]))
        elif state in ("oneshot", "held", "locked"):
            p.setBrush(QColor(t["latched"]))
        elif self.underMouse():
            p.setBrush(grad(face, t["hover"], t["key_middle"], t["key_bottom"]))
        else:
            p.setBrush(grad(face, t["key_top"], t["key_middle"], t["key_bottom"]))
        if state == "locked":                    # locked: outlined, so it's never mistaken for a tap
            p.setPen(QPen(QColor("#8fb8dd"), 2 * sc))
        p.drawRoundedRect(face.adjusted(sc, sc, -sc, -sc) if state == "locked" else face, r, r)
        p.setPen(QColor("black" if state == "busy" else t["legend"]))
        p.setFont(self.font())
        icon, text = self.icon(), self.text()
        if not icon.isNull():
            isz = self.iconSize()
            gap = 4 * sc if text else 0
            tw = p.fontMetrics().horizontalAdvance(text) if text else 0
            x0 = face.center().x() - (isz.width() + gap + tw) / 2
            pm = icon.pixmap(isz)
            p.drawPixmap(int(x0), int(face.center().y() - isz.height() / 2), pm)
            if text:
                p.drawText(QRectF(x0 + isz.width() + gap, face.top(), tw + 2, face.height()),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        elif text:
            p.drawText(face, Qt.AlignmentFlag.AlignCenter, text)
        p.end()


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
        self.setWindowTitle(_("Arrow Pad (VR)") if TARGET == "vr" else _("Arrow Pad"))
        self.yd = yd
        self.mod_state = {m: "off" for m in MODIFIERS}   # off | oneshot | locked
        self.mod_tapped = {m: 0.0 for m in MODIFIERS}
        self.layer = "nav"
        self.drag_offset = None
        cfg = self.load_config()
        self.cfg = cfg
        self.overlay = None
        self.scale = cfg.get("scale", 1.5 if TARGET == "vr" else scale)   # VR: texture sharpness
        self.pinned = cfg.get("pinned", False)
        THEME.update(THEMES.get(cfg.get("theme", "graphite"), THEMES["graphite"]))
        self.haptic_level = cfg.get("haptics", "normal") if cfg.get("haptics") in HAPTIC_LEVELS else "normal"
        self.mod_pressing = {}          # modifier held down by a laser -> used in a chord yet?

        outer = QVBoxLayout(self)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)   # window = content size
        self.outer = outer
        self.haptics = None
        self.hover_filter = HoverHaptics(self)
        # toolbar: pin, reset position, smaller, larger ......... close
        bar = QHBoxLayout()
        self.tools = {}
        for name in ("settings", "pin", "reset", "smaller", "larger"):
            self.tools[name] = self.tool_button(name, _(TOOL_TIPS[name]))
            bar.addWidget(self.tools[name])
        bar.addStretch(1)
        # Collapse / Expand (chevrons, as on Screen snip's panel), left of Close.
        self.collapsed, self.toggled, self.settings_were_open = False, False, False
        self.tools["fold"] = self.tool_button("fold", _(TOOL_TIPS["fold"]))
        bar.addWidget(self.tools["fold"])
        self.tools["close"] = self.tool_button("close", _(TOOL_TIPS["close"]))
        bar.addWidget(self.tools["close"])
        self.click_swap = ClickSwap(self.restyle)
        outer.addLayout(bar)
        self.tools["pin"].clicked.connect(self.toggle_pin)
        self.tools["settings"].clicked.connect(self.toggle_settings)
        self.tools["reset"].clicked.connect(self.reset_position)
        self.tools["smaller"].clicked.connect(lambda: self.resize_step(-1))
        self.tools["larger"].clicked.connect(lambda: self.resize_step(+1))
        self.tools["close"].clicked.connect(self.close)
        self.tools["fold"].clicked.connect(self.toggle_collapsed)

        grid = QGridLayout()
        self.grid = grid
        self.buttons = []
        for r, row in enumerate(LAYERS["nav"]):
            for c, _key in enumerate(row):
                b = KeyButton(self)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.pressed.connect(lambda r=r, c=c: self.on_press(r, c))
                b.released.connect(lambda r=r, c=c: self.on_release(r, c))
                b.installEventFilter(self.hover_filter)
                grid.addWidget(b, r, c)
                self.buttons.append((r, c, b))
        self.keys_page = QWidget()
        self.keys_page.setLayout(grid)
        outer.addWidget(self.keys_page)
        self.settings_page = self.make_settings_page()
        self.settings_page.hide()
        outer.addWidget(self.settings_page)

        self.apply_scale()
        QTimer(self, interval=500, timeout=self.refresh_mic).start()
        if i18n is not None:              # (the installer window announces a new language: no polling)
            i18n.follow_announcements(self, self.retranslate)
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
        if cfg.get("collapsed"):
            self.toggle_collapsed(place=False)       # (as it was left; it opens where it was)

    def tool_button(self, name, tip):
        b = QPushButton()
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setProperty("tool", "true")
        b.setToolTip(tip)
        icon = icon_for(name)
        if icon:
            b.setIcon(icon)
        else:
            b.setText({"pin": "📌", "reset": "⌖", "smaller": "−", "larger": "+", "close": "✕",
                       "settings": "⚙"}[name])
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
        for _r, _c, b in self.buttons:
            b.setFixedSize(key, key)
            b.setIconSize(QSize(round(key * 0.45), round(key * 0.45)))
        for b in self.setting_buttons.values():
            b.setFixedHeight(round(key * 0.8))
            f = QFont(QApplication.font())
            f.setPixelSize(round(key * 0.28))
            b.setFont(f)
        for lab in self.setting_labels:
            f = QFont(QApplication.font())
            f.setPixelSize(round(key * 0.26))
            lab.setFont(f)
        self.relabel()
        self.keys_page.adjustSize()
        # Same size as the keys, so the VR panel keeps its shape when settings open.
        self.settings_page.setFixedSize(self.keys_page.sizeHint())
        self.adjustSize()
        if not self.collapsed:
            self.expanded_size = self.size()      # (the VR panel's metres per pixel come from it)

    def show_fold(self):
        b = self.tools["fold"]
        b.setIcon(icon_for("unfold" if self.collapsed else "fold"))
        b.setToolTip(_(TOOL_TIPS["unfold" if self.collapsed else "fold"]))

    def toggle_collapsed(self, place=True):
        """Collapse to just the chevron (now Expand), or back. Its icon stays where it was, under
        the pointer: the window moves (in VR, the overlay moves the panel: vroverlay.render)."""
        fold = self.tools["fold"]
        before = fold.mapToGlobal(fold.rect().center())
        self.collapsed = not self.collapsed
        self.toggled = place
        if self.collapsed:
            self.settings_were_open = self.settings_page.isVisible()
        for name, b in self.tools.items():
            if name != "fold":
                b.setVisible(not self.collapsed)
        self.keys_page.setVisible(not self.collapsed and not self.settings_were_open)
        self.settings_page.setVisible(not self.collapsed and self.settings_were_open)
        self.show_fold()
        self.adjustSize()
        self.layout().activate()
        if place and not self.overlay:
            self.move(self.pos() + before - fold.mapToGlobal(fold.rect().center()))
        self.cfg["collapsed"] = self.collapsed
        self.save_config()

    def pivot(self):
        """The chevron's centre (widget pixels): the VR panel keeps it still on Collapse / Expand."""
        fold = self.tools["fold"]
        return fold.mapTo(self, fold.rect().center())

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

    @property
    def lang(self):
        """The language the keys are shown in (the VR overlay draws again when it changes)."""
        return i18n.CATALOGUE.language if i18n is not None else None

    def label(self, name):
        if name in WORDS:
            return pgettext("key legend", WORDS[name])
        if name in LEGENDS:
            legend = pgettext("key legend", name)
            if legend == name and i18n is not None and i18n.CATALOGUE.language:
                legend = SEED_LEGENDS.get(i18n.CATALOGUE.language.split("_")[0], {}).get(name, name)
            return legend
        return name

    def retranslate(self):
        """The installer window switched language: the keys, tooltips and settings in it too."""
        self.setWindowTitle(_("Arrow Pad (VR)") if TARGET == "vr" else _("Arrow Pad"))
        for name, b in self.tools.items():
            b.setToolTip(_(TOOL_TIPS[name]))
        self.show_fold()
        showing = self.settings_page.isVisible()
        old, self.settings_page = self.settings_page, self.make_settings_page()
        self.outer.replaceWidget(old, self.settings_page)
        old.deleteLater()
        self.settings_page.setVisible(showing)
        self.relabel()
        self.apply_scale()

    def relabel(self):
        key = round(52 * self.scale)
        for r, c, b in self.buttons:
            name = self.name_at(r, c)
            b.setToolTip(_(TIPS[name]).format(m=self.label(name)) if name in TIPS else "")
            icon = icon_for(name) if name in CHORDS or name in MOUSE or name in ("Super", "Launcher", "Snip") else None
            if icon:
                b.setIcon(icon)
                # (the two mouse icons look alike: the button's initial, in the user's language)
                b.setText(pgettext("mouse button", MOUSE_WORDS[name])[:1].upper() if name in MOUSE_WORDS else "")
                if name in MOUSE:
                    f = QFont(QApplication.font())
                    f.setPixelSize(round(key * 0.24))
                    f.setBold(True)
                    b.setFont(f)
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

    def name_at(self, r, c):
        return LAYERS[self.layer][r][c]

    def restyle(self):
        for (title, key), b in getattr(self, "setting_buttons", {}).items():
            chosen = (title == "Theme" and THEME["name"] == THEMES[key]["name"]) or \
                     (title == "Haptics" and self.haptic_level == key)
            self.set_state(b, "locked" if chosen else "off")
        for r, c, b in self.buttons:
            name = self.name_at(r, c)
            if name in MODIFIERS:
                state = self.mod_state[name]
            elif name in ("Fn", "Tools"):
                state = "locked" if self.layer == {"Fn": "fn", "Tools": "tools"}[name] else "off"
            elif name in MOUSE:
                state = "locked" if self.click_swap.armed == name else "off"
            elif name == "🎤":
                state = {"recording": "active", "transcribing": "busy"}.get(self.dictation_state(), "off")
            else:
                state = "off"
            self.set_state(b, state)
        # Pin shows its state by icon, like Full Keyboard (no highlight behind it).
        pin = self.tools["pin"]
        icon = icon_for("pin_on" if self.pinned else "pin")
        if icon and pin.property("pinned") != self.pinned:
            pin.setIcon(icon)
            pin.setProperty("pinned", self.pinned)
        pin.setToolTip(_("Pinned: tap to allow moving") if self.pinned else _("Pin: stop accidental moves"))

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

    # ---- settings (theme, haptic strength), like Full Keyboard's settings menu ----------------
    def make_settings_page(self):
        from PyQt6.QtWidgets import QLabel
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        self.setting_buttons, self.setting_labels = {}, []
        for title, options in (("Theme", [(k, _(v["name"])) for k, v in THEMES.items()]),
                               ("Haptics", [(k, _(HAPTIC_NAMES[k])) for k in HAPTIC_LEVELS])):
            lab = QLabel(_(SETTING_TITLES[title]))
            self.setting_labels.append(lab)
            lay.addWidget(lab)
            row = QHBoxLayout()
            for key, label in options:
                b = KeyButton(self)
                b.setText(label)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.clicked.connect(lambda _=False, t=title, k=key: self.choose_setting(t, k))
                self.setting_buttons[(title, key)] = b
                row.addWidget(b)
            lay.addLayout(row)
        lay.addStretch(1)
        done = KeyButton(self)
        done.setText(_("Done"))
        done.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        done.clicked.connect(self.toggle_settings)
        self.setting_buttons[("", "done")] = done
        lay.addWidget(done)
        return page

    def toggle_settings(self):
        showing = self.settings_page.isVisible()
        self.settings_page.setVisible(not showing)
        self.keys_page.setVisible(showing)
        self.set_state(self.tools["settings"], "off" if showing else "locked")
        self.restyle()

    def choose_setting(self, title, key):
        if title == "Theme":
            THEME.update(THEMES[key])
            self.cfg["theme"] = key
            self.setStyleSheet(stylesheet(self.scale))
            self.update()
        else:
            self.haptic_level = key
            self.cfg["haptics"] = key
            self.pulse("press")              # feel the new strength
        self.restyle()
        self.save_config()

    def toggle_click(self, which):
        self.click_swap.arm(which)
        self.restyle()

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
        strength = HAPTIC_LEVELS.get(self.haptic_level, 1.0)
        if self.haptics and strength > 0:
            self.haptics.pulse(kind, device, strength)

    def on_press(self, r, c):
        self.pulse("press")
        name = self.name_at(r, c)
        if name in MODIFIERS:
            # Two hands, like Full Keyboard: a modifier is down while a laser holds it, so a key
            # pressed with the other hand gets it. Released after that, it was only a chord.
            if self.mod_state[name] == "off":
                self.yd.key(KEY[name], True)
                self.mod_state[name] = "held"
                self.restyle()
            self.mod_pressing[name] = False
            return
        for m in self.mod_pressing:
            self.mod_pressing[m] = True        # used in a chord
        if name in KEY:
            self.yd.key(KEY[name], True)

    def on_release(self, r, c):
        name = self.name_at(r, c)
        if self.overlay is not None:
            self.overlay.log_input(f"     released {name!r} (row {r}, col {c})")
        if name in MODIFIERS:
            chord = self.mod_pressing.pop(name, False)
            if self.mod_state[name] == "held":
                if chord:                        # held for a key from the other hand: done
                    self.mod_state[name] = "off"
                    self.yd.key(KEY[name], False)
                else:                            # a plain tap: one-shot (it's already down)
                    self.mod_state[name] = "oneshot"
                    self.mod_tapped[name] = time.monotonic()
                self.restyle()
            else:
                self.toggle_mod(name)
        elif name == "Launcher":
            self.yd.tap(KEY["Super"])
        elif name in ("Fn", "Tools"):
            target = {"Fn": "fn", "Tools": "tools"}[name]
            self.layer = target if self.layer != target else "nav"
            self.relabel()
        elif name == "Snip":
            self.snip()
        elif name == "Unstick":
            self.unstick()
        elif name in MOUSE:
            self.toggle_click(name)
        elif name == "🎤":
            subprocess.Popen([str(Path.home() / ".local/bin/dictate")], start_new_session=True)
            QTimer.singleShot(300, self.restyle)
        elif name in CHORDS:
            ctrl_held = self.mod_state["Ctrl"] != "off"
            keys = CHORDS[name] if isinstance(CHORDS[name], tuple) else (CHORDS[name],)
            codes = ([] if ctrl_held else [KEY["Ctrl"]]) + [KEY[k] for k in keys]
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
            if s == "oneshot" and m not in self.mod_pressing:
                self.mod_state[m] = "off"
                self.yd.key(KEY[m], False)
        self.restyle()

    def release_all_mods(self):
        self.mod_pressing.clear()
        for m, s in self.mod_state.items():
            if s != "off":
                self.yd.key(KEY[m], False)
                self.mod_state[m] = "off"

    # ---- stuck keys -----------------------------------------------------
    def unstick(self):
        """The desktop can miss a key's release (focus moved to another VR window while it was
        held) and keep acting as if Shift, Ctrl, Alt or Super were down: send each one a full
        press and release, and let go of the pad's own modifiers."""
        self.release_all_mods()
        self.yd.clear_stuck_modifiers()
        self.restyle()
        subprocess.Popen(["notify-send", "-a", _("Arrow Pad"), _("Keys released"),
                          _("Shift, Ctrl, Alt and Super were pressed and let go.")], start_new_session=True)

    # ---- screen snip (snip/ tweak) --------------------------------------
    def snip(self):
        tool = Path.home() / ".local/bin/frame-snip"
        if tool.exists():
            # Its own process and session: the selection window opens on the Steam session's display.
            subprocess.Popen([str(tool)], start_new_session=True)
        else:
            subprocess.Popen(["notify-send", "-a", _("Arrow Pad"), _("Screen snip isn't installed"),
                              _("Tick 'Screen snip + Narrate' in Frame Tweaks to use this button.")],
                             start_new_session=True)

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
            self.click_swap.disarm("pad hidden")
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
            self.cfg.update({"pos": [self.x(), self.y()], "scale": self.scale, "pinned": self.pinned,
                             "haptics": self.haptic_level})
            CONFIG.write_text(json.dumps(self.cfg))
        except OSError:
            pass

    def closeEvent(self, ev):
        self.save_config()
        self.release_all_mods()   # never leave a modifier stuck down
        self.click_swap.disarm()  # nor the pointer grabbed
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
    # A crash in native code (ctypes, Qt, OpenVR) kills the pad without a Python traceback; keep
    # one in a file so a bug report can say where it happened.
    try:
        import faulthandler
        main.crash_log = open(RUN / f"arrowpad-{TARGET}-crash.log", "a")
        faulthandler.enable(file=main.crash_log, all_threads=True)
    except OSError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scale", type=float, default=float(os.environ.get("ARROWPAD_SCALE", 1.0)),
                    help=_("button size multiplier (default 1.0)"))
    ap.add_argument("--socket", default=default_socket(), help=_("ydotoold socket path"))
    ap.add_argument("--quit", action="store_true", help=_("close a running pad"))
    ap.add_argument("--desktop", action="store_true", help=_("open in desktop mode (even from the VR menu)"))
    ap.add_argument("--vr", action="store_true", help=_("open as a floating VR window"))
    args = ap.parse_args()

    # Hand "quit"/"toggle" to a running pad before any window code starts: --quit must work
    # from anywhere (an uninstall in a terminal can't open desktop mode's display).
    if signal_running("quit" if args.quit else "toggle") or args.quit:
        return
    app = QApplication(sys.argv)
    app.setApplicationName("arrowpad")
    # Taskbar/window icon instead of the generic X11 logo; the desktop file name lets
    # KWin match the window to its menu entry.
    app.setDesktopFileName("arrowpad-vr" if TARGET == "vr" else "arrowpad")
    if ICON.exists():
        app.setWindowIcon(QIcon(str(ICON)))
    try:
        yd = Ydotool(args.socket)
        yd.clear_stuck_modifiers()
    except OSError as e:
        sys.exit(_("arrowpad: cannot reach ydotoold at {socket}: {error}\n"
                   "Start it with: systemctl --user start ydotoold").format(socket=args.socket, error=e))

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
