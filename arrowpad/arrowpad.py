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

from PyQt6.QtCore import QPoint, Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QIcon  # noqa: E402
from PyQt6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QGridLayout, QPushButton,  # noqa: E402
                             QWidget)

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
TIPS = {"🎤": "Dictation: tap to start (red), tap again to stop; yellow = transcribing, then it types",
        "All": "Select all (Ctrl+A)", "Undo": "Undo (Ctrl+Z)", "Fn": "F1–F12 layer",
        **{m: f"{m}: tap = next key only, double-tap = lock" for m in MODIFIERS}}
DOUBLE_TAP = 0.4
RUN = Path(f"/run/user/{os.getuid()}")
CONFIG = Path.home() / f".config/arrowpad{'-vr' if TARGET == 'vr' else ''}.json"
SERVER_NAME = f"arrowpad-{os.getuid()}-{TARGET}"   # desktop and VR pads are separate instances
ICON = Path.home() / ".local/share/icons/hicolor/256x256/apps/frame-tweaks-arrowpad.png"
STYLE = """
QWidget#pad { background: palette(window); }
QPushButton { border-radius: 6px; }
QPushButton[state="oneshot"] { background: #3d7bd9; color: white; }
QPushButton[state="locked"]  { background: #1f4f99; color: white; border: 2px solid #9cc2ff; }
QPushButton[state="active"]  { background: #c0392b; color: white; }
QPushButton[state="busy"]    { background: #d9a400; color: black; }
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

    def tap(self, *codes):
        for c in codes:
            self.key(c, True)
        for c in reversed(codes):
            self.key(c, False)


class ArrowPad(QWidget):
    def __init__(self, yd, scale):
        super().__init__(None, Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setObjectName("pad")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Arrow Pad" + (" (VR)" if TARGET == "vr" else ""))
        self.setStyleSheet(STYLE)
        self.yd = yd
        self.mod_state = {m: "off" for m in MODIFIERS}   # off | oneshot | locked
        self.mod_tapped = {m: 0.0 for m in MODIFIERS}
        self.layer = "nav"
        self.buttons = []
        size = int(52 * scale)
        grid = QGridLayout(self)
        grid.setSpacing(4)
        grid.setContentsMargins(6, 6, 6, 6)
        for r, row in enumerate(LAYERS["nav"]):
            for c, _ in enumerate(row):
                b = QPushButton()
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.setFixedSize(size, size)
                b.pressed.connect(lambda r=r, c=c: self.on_press(r, c))
                b.released.connect(lambda r=r, c=c: self.on_release(r, c))
                grid.addWidget(b, r, c)
                self.buttons.append((r, c, b))
        self.scale = scale
        self.relabel()
        self.mic_timer = QTimer(self, interval=500, timeout=self.refresh_mic)
        self.mic_timer.start()
        self.restore_position()

    # ---- layout / looks -------------------------------------------------
    def name_at(self, r, c):
        return LAYERS[self.layer][r][c]

    def relabel(self):
        for r, c, b in self.buttons:
            name = self.name_at(r, c)
            b.setText(name)
            b.setToolTip(TIPS.get(name, ""))
            f = QApplication.font()
            f.setPointSizeF(f.pointSizeF() * self.scale * (1.6 if len(name) == 1 else 1.0))
            b.setFont(f)
        self.restyle()

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
            if b.property("state") != state:
                b.setProperty("state", state)
                b.style().unpolish(b)
                b.style().polish(b)

    # ---- input ----------------------------------------------------------
    def on_press(self, r, c):
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

    # ---- window ---------------------------------------------------------
    def toggle_visible(self):
        if self.isVisible():
            self.save_position()
            self.release_all_mods()
            self.hide()
        else:
            self.show()
            self.raise_()

    def restore_position(self):
        try:
            pos = json.loads(CONFIG.read_text()).get("pos")
            if pos:
                self.move(QPoint(*pos))
        except (OSError, ValueError):
            pass

    def save_position(self):
        try:
            CONFIG.write_text(json.dumps({"pos": [self.x(), self.y()]}))
        except OSError:
            pass

    def closeEvent(self, ev):
        self.save_position()
        self.release_all_mods()   # never leave a modifier stuck down
        super().closeEvent(ev)


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
