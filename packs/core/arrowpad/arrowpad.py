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
import array
import fcntl
import gettext
import json
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.environ.get("FRAME_TWEAKS_PYLIB") or str(Path.home() / ".local/share/frame-tweaks/i18n"))   # (lib/common.sh install_i18n)
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


def desktop_env():
    """Desktop mode's environment (its session manager's), or None when it isn't running."""
    src = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "ksmserver"],
                         capture_output=True, text=True).stdout.split()
    if not src:
        return None
    text = Path(f"/proc/{src[0]}/environ").read_text(errors="replace")
    return dict(kv.split("=", 1) for kv in text.split("\0") if "=" in kv)


def pick_display(argv):
    """--desktop / --vr choose where the pad opens, whichever menu launched it.
    Desktop mode is a nested Plasma session with its own X display (:2 here) and
    X authority file; VR floating windows live on the Steam session's display :0."""
    if "--desktop" in argv:
        env = desktop_env()
        if env is None:
            sys.exit(_("arrowpad: desktop mode isn't running"))
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

from PyQt6.QtCore import (QEvent, QObject, QPoint, QRectF, QSize, Qt, QtMsgType, QTimer, pyqtSignal,  # noqa: E402
                          qFormatLogMessage, qInstallMessageHandler)
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath  # noqa: E402
from PyQt6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLayout, QPushButton,  # noqa: E402
                             QVBoxLayout, QWidget)

import ftconf  # noqa: E402  (settings files and logs: lib/ftconf.py, installed beside i18n.py)
import needs  # noqa: E402  ("this needs a tweak that isn't installed": lib/needs.py, the same)
try:
    import xkb  # noqa: E402  (keys on the desktop's keyboard layout: lib/xkb.py, the same)
except ImportError:                       # (without it: the keys of a US keyboard, as before)
    xkb = None

try:  # controller haptics (optional): SteamVR Input via the openvr module
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from haptics import Haptics  # noqa: E402
except Exception:  # pragma: no cover
    Haptics = None

# Linux input-event-codes.h
EV_SYN, EV_KEY, SYN_REPORT = 0x00, 0x01, 0
KEY_RIGHTCTRL = 97                       # (toggles the nested desktop's input grab: only Unstick sends it, when it's on)
KEY_NAMES = {1: "Esc", 14: "Backspace", 15: "Tab", 28: "Enter", 29: "Ctrl", 42: "Shift", 54: "Shift", 56: "Alt",
             57: "Space", 97: "Right Ctrl", 100: "AltGr", 125: "Super", 126: "Super"}


def key_name(code):
    return KEY_NAMES.get(code, _("key {code}").format(code=code))


def keyboards(text=None):
    """{"/dev/input/eventN": device name} for keyboards and mice: devices with an A key or a left
    button (not the power button, the gamepad or the like). text: /proc/bus/input/devices."""
    devs = {}
    try:
        text = Path("/proc/bus/input/devices").read_text() if text is None else text
    except OSError:
        return devs
    for blk in text.split("\n\n"):
        name = re.search(r'N: Name="([^"]*)"', blk)
        ev = re.search(r"H: Handlers=.*\b(event\d+)", blk)
        keys = re.search(r"B: KEY=([0-9a-f ]+)", blk)
        if not (name and ev and keys):
            continue
        bits = 0                                         # (the bitmap: words, most significant first)
        for word in keys[1].split():
            bits = (bits << (8 * struct.calcsize("l"))) | int(word, 16)
        if bits >> 30 & 1 or bits >> 0x110 & 1:          # KEY_A, BTN_LEFT
            devs[f"/dev/input/{ev[1]}"] = name[1]
    return devs


def held_keys(path):
    """The keys the kernel has as down on an input device (EVIOCGKEY; the input group may read it)."""
    buf = array.array("B", bytes(96))
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        fcntl.ioctl(fd, (2 << 30) | (len(buf) << 16) | (ord("E") << 8) | 0x18, buf, True)
    finally:
        os.close(fd)
    return [i for i in range(len(buf) * 8) if buf[i // 8] >> (i % 8) & 1]


def release_held_keys(devices=None):
    """Let go of the keys input devices still hold: {device name: [codes]} of what it let go of.
    A Bluetooth keyboard that lost a key's release keeps the key down for every app, and the pad's
    own presses can't release another device's key. A release written to the device's node goes
    to every app as if the keyboard had sent it. (Never Right Ctrl, the desktop's grab key.)"""
    released = {}
    for path, name in (keyboards() if devices is None else devices).items():
        try:
            keys = [k for k in held_keys(path) if k != KEY_RIGHTCTRL]
            if not keys:
                continue
            now = time.time()
            stamp = (int(now), int(now % 1 * 1e6))
            fd = os.open(path, os.O_WRONLY)
            try:
                for k in keys:
                    os.write(fd, struct.pack("llHHi", *stamp, EV_KEY, k, 0))
                os.write(fd, struct.pack("llHHi", *stamp, EV_SYN, SYN_REPORT, 0))
            finally:
                os.close(fd)
        except OSError:                                  # (not readable or writable: not ours to fix)
            continue
        released[name] = keys
    return released


UNSTICK_LOG = Path.home() / ".local/state/frame-tweaks/logs/unstick.log"     # (./install.sh report includes it)


def unstick_log(line):
    try:
        UNSTICK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with UNSTICK_LOG.open("a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + line + "\n")
        lines = UNSTICK_LOG.read_text().splitlines()
        if len(lines) > 200:
            UNSTICK_LOG.write_text("\n".join(lines[-100:]) + "\n")
    except OSError:
        pass


# Desktop mode's window title, KWin's own words: its name, then whether it has taken all input
# ("…to ungrab input": Right Ctrl gives it back) or not ("…key to grab input"). KWin says them in
# desktop mode's language, so they're looked up in its catalogue for that language too.
KWIN_LOCALE = Path("/usr/share/locale")
KWIN_NAME = ("KDE Wayland Compositor",
             ("Title of nested KWin Wayland with Wayland socket identifier as argument", "KDE Wayland Compositor %1"))
KWIN_GRABBED = ("Press right control to ungrab input", "Press right control to ungrab pointer")
KWIN_FREE = ("Press right control key to grab input", "Press right control key to grab pointer")


def desktop_languages():
    """Desktop mode's languages, as KDE picks them (LANGUAGE, LC_ALL, LC_MESSAGES, LANG), else
    this program's and the one Frame Tweaks speaks."""
    try:
        sources = [desktop_env() or os.environ]
    except OSError:
        sources = [os.environ]
    langs = [lang for env in sources for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")
             for lang in env.get(var, "").split(":")]
    if sources[0] is os.environ and i18n is not None:
        langs += i18n.wanted_languages()
    return [lang for lang in dict.fromkeys(langs) if lang and lang.split(".")[0] not in ("C", "POSIX")]


_kwin_words = {}


def kwin_words(languages):
    """KWin's words for the title in English and in these languages: (names, grabbed, free).
    Read once for each set of languages (the VR panel asks every 2 s)."""
    key = (str(KWIN_LOCALE), tuple(languages))
    if key not in _kwin_words:
        _kwin_words[key] = read_kwin_words(languages)
    return _kwin_words[key]


def read_kwin_words(languages):
    catalogues = []
    for mo in gettext.find("kwin", str(KWIN_LOCALE), languages=languages, all=True):
        try:
            with open(mo, "rb") as f:
                catalogues.append(gettext.GNUTranslations(f))
        except Exception:                                # (a damaged catalogue: English, at least)
            continue

    def said(words):
        out = set()
        for w in words:
            out.add(w[1] if isinstance(w, tuple) else w)
            out.update(c.pgettext(*w) if isinstance(w, tuple) else c.gettext(w) for c in catalogues)
        return out
    return said(KWIN_NAME), said(KWIN_GRABBED), said(KWIN_FREE)


def says_grabbed(title, names, grabbed, free):
    """title is desktop mode's window saying it has taken all input: KWin's name for it, then the
    "ungrab" hint, and not the "grab" one."""
    if not any(re.match(re.escape(n).replace("%1", ".*?"), title) for n in names):
        return False
    hints = [g for g in grabbed if g in title]
    for g in hints:
        title = title.replace(g, "")
    return bool(hints) and not any(f in title for f in free)


def desktop_grabbed():
    """Whether desktop mode has taken all input: its window on the Steam session's display then
    says "Press right control to ungrab input", in desktop mode's language. Nothing else counts:
    the answer decides whether Right Ctrl, which toggles that, is sent."""
    try:
        out = subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True, timeout=5,
                             env={**os.environ, "DISPLAY": ":0", "LC_ALL": "C.UTF-8"}).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    # (UTF-8, whatever this program's locale; another window's Latin-1 title, which isn't, crashed the pad)
    titles = re.findall(r'^\s*0x[0-9a-fA-F]+ "(.*)":', out.decode("utf-8", errors="replace"), re.M)
    words = kwin_words(desktop_languages())
    return any(says_grabbed(t, *words) for t in titles)


KEY = {
    "Esc": 1, "Tab": 15, "Bksp": 14, "Del": 111, "Enter": 28, "Ins": 110,
    "Home": 102, "End": 107, "PgUp": 104, "PgDn": 109,
    "↑": 103, "↓": 108, "←": 105, "→": 106,
    "Shift": 42, "Ctrl": 29, "Alt": 56, "Super": 125,
    "PrtSc": 99, "Menu": 127,
    **{f"F{n}": c for n, c in zip(range(1, 11), range(59, 69))}, "F11": 87, "F12": 88,
    # The shortcuts' letters, where a US keyboard has them; sent where the desktop's layout has
    # them (chord_keys: on a French keyboard, A is where Q is here).
    "A": 30, "C": 46, "V": 47, "X": 45, "Z": 44, "F": 33, "S": 31,
}
MODIFIERS = ("Ctrl", "Alt", "Super")
MOUSE = ("RMB", "MMB")       # toggles: the next click becomes a right / middle click
CHORDS = {"Copy": "C", "Paste": "V", "Cut": "X", "Undo": "Z", "All": "A",   # Ctrl + key(s)
          "Redo": ("Shift", "Z"), "Find": "F", "Save": "S"}


def holds(name):
    """name is a key that's down while its button is (arrows, Bksp…): not a modifier, nor a button
    that does something once it's let go (Copy, 🎤, Tools…)."""
    return name in KEY and name not in MODIFIERS


def chord_keys(name):
    """A shortcut's keys after Ctrl, its letter on the desktop's keyboard layout (on a French one
    Ctrl+A was Ctrl+Q, Quit, and on a German one Undo was Ctrl+Y)."""
    keys = CHORDS[name] if isinstance(CHORDS[name], tuple) else (CHORDS[name],)
    return [xkb.letter_key(k, KEY[k]) if xkb is not None and len(k) == 1 else KEY[k] for k in keys]


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


def seed_language():
    """The language for SEED_LEGENDS: the translation's, else the one wanted (a language with no
    translation file has no catalogue, so a German keyboard got the English legends)."""
    if i18n is None:
        return None
    return i18n.CATALOGUE.language or next(iter(i18n.wanted_languages()), None)


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
        self.path = path
        self.connect()

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.connect(self.path)

    def _emit(self, type_, code, value):
        t = time.time()
        event = struct.pack("llHHi", int(t), int((t % 1) * 1_000_000), type_, code, value)
        try:
            self.sock.send(event)
        except OSError:
            # ydotoold was restarted (ydotool's ▶ Restart): this socket still points at the old
            # one. Connect again; if it isn't back yet, the key is lost, not the pad (an error
            # here, inside a button's handler, would abort it).
            try:
                self.sock.close()
                self.connect()
                self.sock.send(event)
            except OSError:
                pass

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
        ftconf.append_log(self.LOG, msg)

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


# drawn_icon below is ported from TaiKeid/steam-frame-full-keyboard (src/panel.cpp, release
# 0.6.0), under its licence:
#
# MIT License
#
# Copyright (c) 2026 TaiKeid and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
def drawn_icon(name, px=96, color=THEME["legend"]):
    """Full Keyboard's vector icons, redrawn with QPainter: same 24-unit coordinates, 1.8-unit
    round strokes, so the toolbar and clipboard keys match it exactly. None for names it doesn't
    draw. (Ported from Full Keyboard: its MIT licence is above.)"""
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
    gradient. State (property "state"): off, oneshot/held/locked (latched), active, busy.

    Qt says "released" each time a held pointer slides off the key, and "pressed" when it slides
    back on (a laser's jitter at a key's edge does both), but "clicked" only once, when it's let
    go on the key. lifted: the press is over, let go on the key or off it."""
    lifted = pyqtSignal()

    def __init__(self, pad):
        super().__init__()
        self.pad = pad
        self._amount = 0.0
        self.pressing = False
        from PyQt6.QtCore import QVariantAnimation
        self.anim = QVariantAnimation(self)
        self.anim.valueChanged.connect(self._set_amount)
        self.pressed.connect(lambda: self._animate(1.0))
        self.released.connect(lambda: self._animate(0.0))

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        if ev.button() == Qt.MouseButton.LeftButton and self.isDown():
            self.pressing = True

    def mouseReleaseEvent(self, ev):
        lift = self.pressing and ev.button() == Qt.MouseButton.LeftButton
        # Let go off the key while Qt still had it down (no move said the pointer had left): Qt then
        # lets go without a word, and a key stayed down. Say "released", as sliding off does.
        silent = lift and self.isDown() and not self.hitButton(ev.position().toPoint())
        super().mouseReleaseEvent(ev)
        if silent:
            self.released.emit()
        if lift:
            self.pressing = False
            self.lifted.emit()

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
        self.seed_lang = seed_language()
        self.drag_offset = None
        cfg = self.load_config()
        self.cfg = cfg
        self.overlay = None
        # VR: texture sharpness. Desktop: --scale / ARROWPAD_SCALE when given, else the saved size.
        self.scale = cfg.get("scale", 1.5) if TARGET == "vr" else scale or cfg.get("scale", 1.0)
        self.pinned = cfg.get("pinned", False)
        THEME.update(THEMES.get(cfg.get("theme", "graphite"), THEMES["graphite"]))
        self.haptic_level = cfg.get("haptics", "normal") if cfg.get("haptics") in HAPTIC_LEVELS else "normal"
        self.mod_pressing = {}          # modifier held down by a laser -> used in a chord yet?
        self.dictation_was = "idle"     # (refresh_mic: Dictation's state at the last look)
        self.held = {}                  # (row, col) -> the key its press sent (the layer can change)

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
        # (a lambda: clicked passes `checked` (False), which would land in place= and skip
        # keeping the chevron under the laser)
        self.tools["fold"].clicked.connect(lambda: self.toggle_collapsed())

        grid = QGridLayout()
        self.grid = grid
        self.buttons = []
        for r, row in enumerate(LAYERS["nav"]):
            for c, _key in enumerate(row):
                b = KeyButton(self)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                # Keys held down (arrows, Bksp…) follow pressed / released; the rest act once, on
                # clicked, and a modifier's press ends when it's lifted (KeyButton).
                b.pressed.connect(lambda r=r, c=c: self.on_press(r, c))
                b.released.connect(lambda r=r, c=c: self.on_release(r, c))
                b.clicked.connect(lambda _=False, r=r, c=c: self.on_click(r, c))
                b.lifted.connect(lambda r=r, c=c: self.let_go_at(r, c))
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
            if legend == name and self.seed_lang:
                legend = SEED_LEGENDS.get(self.seed_lang.split("_")[0], {}).get(name, name)
            return legend
        return name

    def retranslate(self):
        """The installer window switched language: the keys, tooltips and settings in it too."""
        self.seed_lang = seed_language()
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
        if (r, c) in self.held:
            return              # (slid back onto the key it's still pressing: the same press)
        self.pulse("press")
        name = self.held[(r, c)] = self.name_at(r, c)
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
        """Let go on the key, or slid off it: a key held down (↓, Bksp…) goes up. The rest wait for
        the click (let go on the key) or the end of the press (let_go_at): sliding off and back on,
        as a laser's jitter at a key's edge does, pasted three times and started dictation thrice."""
        # The key that was pressed: another laser may have switched the layer meanwhile (holding ↓
        # through a tap on Tools released Redo, and left ↓ held down).
        name = self.held.get((r, c))
        if self.overlay is not None:
            self.overlay.log_input(f"     released {name or self.name_at(r, c)!r} (row {r}, col {c})")
        if holds(name):
            del self.held[(r, c)]
            self.yd.key(KEY[name], False)
            self.release_oneshots()

    def on_click(self, r, c):
        """Let go on the key it pressed (once, however the pointer wandered meanwhile): what the
        button does. A tap on a modifier latches it (one-shot; twice, locked)."""
        name = self.held.pop((r, c), None)
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
            if self.mod_state["Super"] != "off":     # Super already down (latched): letting it go is the tap
                self.mod_state["Super"] = "off"
                self.yd.key(KEY["Super"], False)
            else:
                self.yd.tap(KEY["Super"])
            self.release_oneshots()
        elif name in ("Fn", "Tools"):
            target = {"Fn": "fn", "Tools": "tools"}[name]
            self.layer = target if self.layer != target else "nav"
            self.relabel()
        elif name == "Snip":
            self.release_oneshots()
            self.snip()
        elif name == "Unstick":
            self.unstick()
        elif name in MOUSE:
            self.toggle_click(name)
        elif name == "🎤":
            self.let_go_for_dictation()
            self.dictate()
        elif name in CHORDS:
            ctrl_held = self.mod_state["Ctrl"] != "off"
            self.yd.tap(*([] if ctrl_held else [KEY["Ctrl"]]), *chord_keys(name))
            self.release_oneshots()

    def let_go_at(self, r, c):
        """A press that ends without a click (let go off the key, or taken back): let go of what it
        holds down, its key or a modifier it pressed, without what a click would do (a tap, a
        chord, a layer, dictation…)."""
        name = self.held.pop((r, c), None)
        if name in MODIFIERS:
            self.mod_pressing.pop(name, None)
            if self.mod_state[name] == "held":
                self.mod_state[name] = "off"
                self.yd.key(KEY[name], False)
                self.restyle()
        elif holds(name):
            self.yd.key(KEY[name], False)
            self.release_oneshots()

    def let_go(self, button):
        """The VR overlay took a press back (a grab, the dashboard closing, Close): its release
        came off the key, so it ended without a click (let_go_at, through KeyButton.lifted); this
        makes sure of it."""
        for r, c, b in self.buttons:
            if b is button:
                self.let_go_at(r, c)

    def release_keys(self):
        """Let go of everything the pad holds down, keys and modifiers: it's going away, and
        ydotoold's keyboard is the whole Frame's (a Ctrl left down turns every click into Ctrl+click)."""
        for name in [n for n in self.held.values() if holds(n)]:
            self.yd.key(KEY[name], False)
        self.held.clear()
        self.release_all_mods()

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

    def let_go_for_dictation(self):
        """Dictation types through the same ydotoold: with Ctrl still down, every letter was a
        Ctrl+letter (W closes the tab, Q quits). It lets go of every modifier before it types now,
        however it was started (🎤, a shortcut, the menu), so the pad's latched and locked ones go
        off with it, on 🎤 and when the pad sees dictation start or end: the pad never shows a
        Ctrl that isn't down. Not one a laser holds (letting go ends it). Alt and Super go up
        around F24, as Dictation lets them go: alone, that'd be a tap (a menu bar, the launcher)."""
        F24 = 194
        latched = [m for m, s in self.mod_state.items() if s != "off" and m not in self.mod_pressing]
        tap = any(m in ("Alt", "Super") for m in latched)
        if tap:
            self.yd.key(F24, True)
        for m in latched:
            self.yd.key(KEY[m], False)
            self.mod_state[m] = "off"
        if tap:
            self.yd.key(F24, False)
        if latched:
            self.restyle()

    def release_all_mods(self):
        self.mod_pressing.clear()
        for m, s in self.mod_state.items():
            if s != "off":
                self.yd.key(KEY[m], False)
                self.mod_state[m] = "off"

    # ---- stuck keys -----------------------------------------------------
    def grabbed_by_desktop(self):
        """For the VR panel's note: desktop mode has taken all input."""
        return desktop_grabbed()

    def unstick(self):
        """The desktop can miss a key's release (focus moved to another VR window while it was
        held) and keep acting as if Shift, Ctrl, Alt or Super were down: send each one a full
        press and release, and let go of the pad's own modifiers. A keyboard that lost a key's
        release (Bluetooth) still holds it for everyone: let go of it there too. And say so when
        it's desktop mode that has taken all input (Right Ctrl), which no key release undoes: then
        give it back with a Right Ctrl tap, and check that it did. What it found goes to its log."""
        self.release_all_mods()
        self.yd.clear_stuck_modifiers()
        self.restyle()
        text = _("Shift, Ctrl, Alt and Super were pressed and let go.")
        held = release_held_keys()
        for device, keys in held.items():
            text += " " + _("{device} still held {keys}: released too.").format(
                device=device, keys=", ".join(key_name(k) for k in keys))
        found = "; ".join(f"{d}: {', '.join(key_name(k) for k in ks)}" for d, ks in held.items()) or "nothing"
        if not desktop_grabbed():
            unstick_log(f"held keys released: {found}; desktop mode's input grab: off")
            subprocess.Popen(["notify-send", "-a", _("Arrow Pad"), _("Keys released"), text], start_new_session=True)
            return
        # Right Ctrl toggles the grab, so it's tapped only now, with the title saying it's on; the
        # title shows whether it worked (the grab takes a moment to let go).
        self.yd.tap(KEY_RIGHTCTRL)

        def check():
            if desktop_grabbed():
                more = _("Desktop mode has taken all input, so other windows don't get it, and didn't give it "
                         "back: tap Right Ctrl on a keyboard.")
                unstick_log(f"held keys released: {found}; desktop mode's input grab: on, still on after Right Ctrl")
            else:
                more = _("Desktop mode had taken all input, so other windows didn't get it: given back.")
                unstick_log(f"held keys released: {found}; desktop mode's input grab: on, given back (Right Ctrl)")
            subprocess.Popen(["notify-send", "-a", _("Arrow Pad"), _("Keys released"), text + " " + more],
                             start_new_session=True)
        QTimer.singleShot(600, check)

    # ---- screen snip (snip/ tweak) --------------------------------------
    def snip(self):
        tool = Path.home() / ".local/bin/frame-snip"
        if tool.exists():
            # Its own process and session: the selection window opens on the Steam session's display.
            subprocess.Popen([str(tool)], start_new_session=True)
        else:
            needs.offer("snip", _("Screen snip isn't installed"),
                        _("The Snip button copies, saves, reads or reads aloud part of the screen, with "
                          "Screen snip + Narrate. It isn't installed yet."))

    # ---- dictation ------------------------------------------------------
    def dictate(self):
        """🎤: start or stop Dictation (dictation/ tweak), if it's installed."""
        tool = Path.home() / ".local/bin/dictate"
        if tool.exists():
            subprocess.Popen([str(tool)], start_new_session=True)
            QTimer.singleShot(300, self.restyle)
        else:
            needs.offer("dictation", _("Dictation isn't installed"),
                        _("The 🎤 button types what you say, with Dictation (speech to text, on the Frame "
                          "itself). It isn't installed yet."))

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
        state = self.dictation_state()
        if state != self.dictation_was and "idle" in (state, self.dictation_was):    # started, or ended
            self.let_go_for_dictation()
        self.dictation_was = state
        if self.isVisible():
            self.restyle()

    # ---- window / settings ----------------------------------------------
    def toggle_visible(self):
        if self.overlay:          # VR: relaunching recenters it in front of you (Full Keyboard does too)
            self.overlay.reset_position()
            return
        if self.isVisible():
            self.save_config()
            self.release_keys()
            self.click_swap.disarm("pad hidden")
            self.hide()
        else:
            self.show()
            self.raise_()

    @staticmethod
    def load_config():
        return ftconf.read_json(CONFIG)          # ({} for none, or a damaged file: it used to crash on a list)

    def save_config(self):
        try:
            self.cfg.update({"pos": [self.x(), self.y()], "scale": self.scale, "pinned": self.pinned,
                             "haptics": self.haptic_level})
            ftconf.write_text(CONFIG, json.dumps(self.cfg))
        except OSError:
            pass

    def closeEvent(self, ev):
        self.save_config()
        self.release_keys()       # never leave a modifier (or a key) stuck down
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


def let_go_on_exit(pad):
    """A pad that goes away lets go of what it holds down first (release_keys), not only one that
    is closed. When desktop mode ends, Qt says "The X11 connection broke" and ends the program
    there and then (no closeEvent); so does any fatal message, such as PyQt6's for an error in
    Python it didn't catch (it aborts the pad): its message handler lets go first. A stop
    (SIGTERM: an update, an uninstall) closes the pad as ✕ does."""
    def message(kind, context, text):
        try:
            if "X11 connection broke" in text or kind == QtMsgType.QtFatalMsg:
                pad.release_keys()
            sys.stderr.write(qFormatLogMessage(kind, context, text) + "\n")    # (as Qt would)
        except Exception:                # (this runs inside Qt: an error here would abort the pad)
            pass
    qInstallMessageHandler(message)

    def stop(*_args):
        pad.release_keys()
        QTimer.singleShot(0, pad.close)  # (from the event loop: not in the middle of whatever was running)
    signal.signal(signal.SIGTERM, stop)


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
    # (None when not given: the saved size. argparse converts a string default with type=.)
    ap.add_argument("--scale", type=float, default=os.environ.get("ARROWPAD_SCALE") or None,
                    help=_("button size multiplier (default 1.0)"))
    ap.add_argument("--socket", default=default_socket(), help=_("ydotoold socket path"))
    ap.add_argument("--quit", action="store_true", help=_("close a running pad"))
    ap.add_argument("--fold", action="store_true", help=_("collapse a running pad to its chevron, or expand it"))
    ap.add_argument("--desktop", action="store_true", help=_("open in desktop mode (even from the VR menu)"))
    ap.add_argument("--vr", action="store_true", help=_("open as a floating VR window"))
    args = ap.parse_args()

    # Hand "quit"/"toggle" to a running pad before any window code starts: --quit must work
    # from anywhere (an uninstall in a terminal can't open desktop mode's display).
    if signal_running("quit" if args.quit else "fold" if args.fold else "toggle") or args.quit or args.fold:
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
    let_go_on_exit(pad)
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
        elif cmd == "fold":
            pad.toggle_collapsed()
        else:
            pad.toggle_visible()
    server.newConnection.connect(on_client)

    pad.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
