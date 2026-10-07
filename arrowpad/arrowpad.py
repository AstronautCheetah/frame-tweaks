#!/usr/bin/env python3
"""Arrow Pad: a small always-on-top key pad (arrows, Home/End, PgUp/PgDn, ...)
for SteamOS desktop mode, where the Steam on-screen keyboard has no arrow keys.

How it works
  * The window runs under XWayland with the "does not accept focus" hint, so
    clicking a button never steals keyboard focus from the app you're typing in.
  * Keys are injected as real key down/up events through ydotoold's socket
    (kernel uinput), so they reach any app, Wayland or X11. Holding a button
    holds the key, so the app's normal key-repeat applies.
  * Shift / Ctrl / Alt are sticky toggles (e.g. Shift + arrows to select text).
"""
import argparse
import os
import socket
import struct
import sys
import time

# Must be set before Qt is imported: KWin only honours "no focus" for X11 windows.
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QGridLayout, QPushButton,  # noqa: E402
                             QWidget)

# Linux input-event-codes.h
EV_SYN, EV_KEY, SYN_REPORT = 0x00, 0x01, 0
KEY = {
    "Esc": 1, "Tab": 15, "Bksp": 14, "Del": 111, "Enter": 28,
    "Home": 102, "End": 107, "PgUp": 104, "PgDn": 109,
    "↑": 103, "↓": 108, "←": 105, "→": 106,
    "Shift": 42, "Ctrl": 29, "Alt": 56,
}
LAYOUT = [
    ["Esc", "Tab", "Bksp", "Del", "Enter"],
    ["Shift", "Home", "↑", "End", "PgUp"],
    ["Ctrl", "←", "↓", "→", "PgDn"],
]
MODIFIERS = {"Shift", "Ctrl", "Alt"}


class Ydotool:
    """Minimal client for ydotoold: it accepts raw `struct input_event`
    datagrams on its unix socket and replays them on a uinput device."""

    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.connect(path)

    def _emit(self, type_, code, value):
        t = time.time()
        sec, usec = int(t), int((t % 1) * 1_000_000)
        self.sock.send(struct.pack("llHHi", sec, usec, type_, code, value))

    def key(self, code, down):
        self._emit(EV_KEY, code, 1 if down else 0)
        self._emit(EV_SYN, SYN_REPORT, 0)


def default_socket():
    return os.environ.get("YDOTOOL_SOCKET") or f"/run/user/{os.getuid()}/.ydotool_socket"


class ArrowPad(QWidget):
    def __init__(self, yd, scale):
        super().__init__(None, Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Arrow Pad")
        self.yd = yd
        self.mods = {}
        size = int(56 * scale)
        grid = QGridLayout(self)
        grid.setSpacing(4)
        grid.setContentsMargins(6, 6, 6, 6)
        for r, row in enumerate(LAYOUT):
            for c, name in enumerate(row):
                b = QPushButton(name)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.setFixedSize(size, size)
                f = b.font()
                f.setPointSizeF(f.pointSizeF() * scale * (1.6 if len(name) == 1 else 1.0))
                b.setFont(f)
                if name in MODIFIERS:
                    b.setCheckable(True)
                    b.toggled.connect(lambda on, n=name: self.toggle_mod(n, on))
                    self.mods[name] = b
                else:
                    b.pressed.connect(lambda n=name: self.press(n, True))
                    b.released.connect(lambda n=name: self.press(n, False))
                grid.addWidget(b, r, c)

    def toggle_mod(self, name, on):
        self.yd.key(KEY[name], on)

    def press(self, name, down):
        self.yd.key(KEY[name], down)

    def closeEvent(self, ev):
        for name, b in self.mods.items():  # never leave a modifier stuck down
            if b.isChecked():
                self.yd.key(KEY[name], False)
        super().closeEvent(ev)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scale", type=float, default=float(os.environ.get("ARROWPAD_SCALE", 1.0)),
                    help="button size multiplier (default 1.0)")
    ap.add_argument("--socket", default=default_socket(), help="ydotoold socket path")
    args = ap.parse_args()
    try:
        yd = Ydotool(args.socket)
    except OSError as e:
        sys.exit(f"arrowpad: cannot reach ydotoold at {args.socket}: {e}\n"
                 "Start it with: systemctl --user start ydotoold")
    app = QApplication(sys.argv)
    app.setApplicationName("arrowpad")
    pad = ArrowPad(yd, args.scale)
    pad.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
